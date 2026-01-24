"""
Scheduler Service for Daily Priority Reports

Uses APScheduler to schedule and manage daily priority report delivery to users
with timezone support.
"""

import logging
from typing import Optional, Callable, Any, Dict, Tuple
from datetime import datetime, time
import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.job import Job

logger = logging.getLogger(__name__)


class SchedulerService:
    """Manages scheduled task delivery using APScheduler"""

    def __init__(self):
        """Initialize APScheduler"""
        self.scheduler = AsyncIOScheduler()
        self.jobs: Dict[int, Job] = {}  # user_id -> Job mapping
        logger.info("SchedulerService initialized")

    async def start(self) -> None:
        """Start the scheduler"""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Scheduler started")
        else:
            logger.debug("Scheduler already running")

    async def stop(self) -> None:
        """Stop the scheduler gracefully"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Scheduler stopped")
        else:
            logger.debug("Scheduler not running")

    def _parse_time(self, time_str: str) -> time:
        """
        Parse time string in HH:MM format

        Args:
            time_str: Time string like "08:00" or "14:30"

        Returns:
            datetime.time object

        Raises:
            ValueError: If time format is invalid
        """
        try:
            hour, minute = map(int, time_str.split(":"))
            if not (0 <= hour < 24 and 0 <= minute < 60):
                raise ValueError(f"Invalid time: {time_str}")
            return time(hour=hour, minute=minute)
        except (ValueError, IndexError) as e:
            raise ValueError(f"Invalid time format. Use HH:MM (24-hour): {time_str}") from e

    def _get_timezone(self, timezone_str: str) -> pytz.timezone:
        """
        Get pytz timezone object

        Args:
            timezone_str: Timezone string like "US/Eastern" or "UTC"

        Returns:
            pytz timezone object

        Raises:
            ValueError: If timezone is invalid
        """
        try:
            return pytz.timezone(timezone_str)
        except pytz.exceptions.UnknownTimeZoneError as e:
            logger.warning(f"Unknown timezone: {timezone_str}, falling back to UTC")
            return pytz.UTC

    def _time_to_cron(self, delivery_time: time) -> Tuple[int, int]:
        """
        Convert time object to cron components

        Args:
            delivery_time: time object with hour and minute

        Returns:
            Tuple of (hour, minute) for cron trigger
        """
        return delivery_time.hour, delivery_time.minute

    async def schedule_daily_report(
        self,
        user_id: int,
        delivery_time: str,  # "HH:MM" format
        timezone_str: str,  # "US/Eastern", "UTC", etc
        report_callback: Callable,  # async callback to generate and send report
    ) -> bool:
        """
        Schedule a daily report for a user

        Args:
            user_id: Telegram user ID
            delivery_time: Time to deliver report in HH:MM format (24-hour)
            timezone_str: User's timezone (e.g., "US/Eastern", "Europe/London")
            report_callback: Async callback function to execute (will be called with user_id)

        Returns:
            True if scheduled successfully, False otherwise
        """
        try:
            # Parse inputs
            time_obj = self._parse_time(delivery_time)
            timezone = self._get_timezone(timezone_str)
            hour, minute = self._time_to_cron(time_obj)

            # Remove existing job if present
            await self.cancel_daily_report(user_id)

            # Create cron trigger for daily execution at specified time
            # The timezone parameter ensures it respects the user's timezone
            trigger = CronTrigger(
                hour=hour,
                minute=minute,
                timezone=timezone
            )

            # Schedule the job
            job = self.scheduler.add_job(
                report_callback,
                trigger,
                args=[user_id],
                id=f"daily_report_{user_id}",
                name=f"Daily Report for User {user_id}",
                replace_existing=True,
                misfire_grace_time=300,  # Allow 5 minute grace period for misfired jobs
            )

            self.jobs[user_id] = job

            logger.info(
                f"Scheduled daily report for user {user_id} at {delivery_time} {timezone_str}"
            )
            return True

        except ValueError as e:
            logger.error(f"Invalid schedule configuration for user {user_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to schedule daily report for user {user_id}: {e}")
            return False

    async def cancel_daily_report(self, user_id: int) -> bool:
        """
        Cancel scheduled daily report for a user

        Args:
            user_id: Telegram user ID

        Returns:
            True if cancelled successfully, False if no job found
        """
        try:
            job_id = f"daily_report_{user_id}"

            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
                if user_id in self.jobs:
                    del self.jobs[user_id]
                logger.info(f"Cancelled daily report for user {user_id}")
                return True
            else:
                logger.debug(f"No scheduled job found for user {user_id}")
                return False

        except Exception as e:
            logger.error(f"Failed to cancel daily report for user {user_id}: {e}")
            return False

    async def reschedule_daily_report(
        self,
        user_id: int,
        new_delivery_time: str,
        new_timezone: str,
        report_callback: Callable,
    ) -> bool:
        """
        Update the schedule for an existing daily report

        Args:
            user_id: Telegram user ID
            new_delivery_time: New delivery time in HH:MM format
            new_timezone: New timezone
            report_callback: Report generation callback

        Returns:
            True if rescheduled successfully
        """
        logger.info(f"Rescheduling report for user {user_id}")
        return await self.schedule_daily_report(
            user_id, new_delivery_time, new_timezone, report_callback
        )

    def get_scheduled_jobs(self) -> Dict[int, Dict[str, Any]]:
        """
        Get information about all scheduled jobs

        Returns:
            Dictionary with user_id -> job_info mapping
        """
        jobs_info = {}

        for user_id, job in self.jobs.items():
            if job:
                jobs_info[user_id] = {
                    "user_id": user_id,
                    "id": job.id,
                    "name": job.name,
                    "next_run_time": job.next_run_time,
                    "trigger": str(job.trigger),
                }

        return jobs_info

    def get_user_schedule(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Get schedule information for a specific user

        Args:
            user_id: Telegram user ID

        Returns:
            Job info dict or None if no job scheduled
        """
        job = self.jobs.get(user_id)

        if job:
            return {
                "user_id": user_id,
                "id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time,
                "trigger": str(job.trigger),
            }

        return None

    def is_job_scheduled(self, user_id: int) -> bool:
        """
        Check if a user has a scheduled report

        Args:
            user_id: Telegram user ID

        Returns:
            True if job is scheduled
        """
        return user_id in self.jobs and self.jobs[user_id] is not None

    async def list_all_jobs(self) -> list:
        """
        Get all scheduled jobs

        Returns:
            List of all APScheduler jobs
        """
        return self.scheduler.get_jobs()

    def get_scheduler_status(self) -> Dict[str, Any]:
        """
        Get current scheduler status

        Returns:
            Dictionary with scheduler info
        """
        return {
            "running": self.scheduler.running,
            "total_jobs": len(self.scheduler.get_jobs()),
            "scheduled_users": len(self.jobs),
            "jobs": [
                {
                    "user_id": user_id,
                    "next_run": str(job.next_run_time) if job else None,
                }
                for user_id, job in self.jobs.items()
            ],
        }


# Singleton instance
_scheduler_service: Optional[SchedulerService] = None


def get_scheduler_service() -> SchedulerService:
    """
    Get or create the singleton SchedulerService instance

    Returns:
        SchedulerService instance
    """
    global _scheduler_service
    if _scheduler_service is None:
        _scheduler_service = SchedulerService()
    return _scheduler_service


if __name__ == "__main__":
    # Example usage
    import asyncio

    async def example_callback(user_id: int):
        print(f"Callback for user {user_id}")

    async def main():
        scheduler = SchedulerService()
        await scheduler.start()

        # Schedule a report for 8:00 AM Eastern Time
        await scheduler.schedule_daily_report(
            user_id=12345,
            delivery_time="08:00",
            timezone_str="US/Eastern",
            report_callback=example_callback,
        )

        status = scheduler.get_scheduler_status()
        print(f"Scheduler Status: {status}")

        # Keep running for a bit
        await asyncio.sleep(5)

        await scheduler.stop()

    asyncio.run(main())
