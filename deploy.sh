#!/bin/bash


sudo cp -f /root/pro/tg-note/etc/systemd/system/tgnote.service /etc/systemd/system/tgnote.service


echo "   启动-tgnote.service"
sudo systemctl enable tgnote.service
sudo systemctl start tgnote.service
sudo systemctl status tgnote.service --no-pager


