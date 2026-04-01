# 每分钟自动同步一次
(crontab -l 2>/dev/null; echo "* * * * * /usr/bin/joplin sync") | crontab -

# 删掉定时任务
crontab -l | grep -v "joplin sync" | crontab -

# 查看定时任务
crontab -l


{
	"$schema": "https://joplinapp.org/schema/settings.json",
	"altInstanceId": "",
	"locale": "en_US",
	"markdown.plugin.softbreaks": false,
	"markdown.plugin.typographer": false,
	"clipperServer.autoStart": true,
	"api.token": "c522cf74e0152627814e2fa3e3f0ac98004a882d2ca5fc25823c43f3170e9fc98ec5d4f4dca496c151218293bca9fd8996eb2bf6026ced220a617d800d7e78c5"
}
