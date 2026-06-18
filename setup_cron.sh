#!/bin/bash
crontab -r 2>/dev/null
(
echo "5 0 * * * cd /home/ubuntu/daily-asset && /home/ubuntu/daily-asset/venv/bin/python3 full_asset_status/run_full_btc.py >> /home/ubuntu/daily-asset/cron.log 2>&1"
echo "10 0 * * * cd /home/ubuntu/daily-asset && /home/ubuntu/daily-asset/venv/bin/python3 multi_asset_status/run_multi_stock.py >> /home/ubuntu/daily-asset/cron.log 2>&1"
echo "0 23 * * * cd /home/ubuntu/daily-asset && /home/ubuntu/daily-asset/venv/bin/python3 fund_status/run_fund_status.py >> /home/ubuntu/daily-asset/cron.log 2>&1"
) | crontab -
echo "Crontab set:"
crontab -l
