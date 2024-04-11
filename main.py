import csv
import os
import sys
from termios import tcflush, TCIOFLUSH
from timedinput import timedinput
import time
from datetime import datetime, date
import schedule
import resend
import logging
import shutil
import config

CSV_FILE_NAME = "attendance.csv"

resend.api_key = config.api_key

# Configure logging
logging.basicConfig(
    filename="rad_raspberry.log",
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s]: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def setup_csv_file():
    with open(CSV_FILE_NAME, mode="w", encoding="UTF8") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["Penn ID", "Badge ID", "All Swipe Data", "Badge Swipe Time"]
        )


def send_email():
    try:
        shutil.copy(
            CSV_FILE_NAME,
            "backup-" + date.today().strftime("%Y-%m-%d.csv"),
        )  # Copy the working attendance file and save it as a backup
        with open(CSV_FILE_NAME, mode="r", encoding="UTF8") as f:
            try:
                email = resend.Emails.send(
                    {
                        "from": config.from_email,
                        "to": config.to_emails,
                        "subject": config.email_subject
                        + date.today().strftime(" (%A, %B %d, %Y)"),
                        "html": f.read(),
                    }
                )
                logging.info(f"Email sent: {email}")
            except Exception as e:
                logging.error(
                    f"An error occurred in sending an email: {str(e)}"
                )

        # Reset the CSV file
        setup_csv_file()
    except Exception as e:
        logging.error(
            f"An error occurred in backing up the attendance file: {str(e)}"
        )


# Schedule the email
schedule.every().monday.at(config.close_time).do(send_email)
schedule.every().tuesday.at(config.close_time).do(send_email)
schedule.every().wednesday.at(config.close_time).do(send_email)
schedule.every().thursday.at(config.close_time).do(send_email)
schedule.every().friday.at(config.close_time).do(send_email)

while True:
    now = datetime.now()
    today_open_time = now.replace(
        hour=int(config.open_time.split(":")[0]),
        minute=int(config.open_time.split(":")[1]),
        second=0,
        microsecond=0,
    )
    today_close_time = now.replace(
        hour=int(config.close_time.split(":")[0]),
        minute=int(config.close_time.split(":")[1]),
        second=0,
        microsecond=0,
    )

    if now > today_open_time and now < today_close_time:  # If accepting swipes
        tcflush(sys.stdin, TCIOFLUSH)  # Flush stdin before taking new input
        card_info = timedinput(
            "Swipe badge: ", timeout=config.swipe_timeout, default="TIMEOUT"
        )
        if (
            card_info != "TIMEOUT"
            and card_info.count("=") == 2
            and len(card_info) > 15
        ):  # If the input didn't time out and format basically makes sense
            penn_id = card_info.split("?")[0].split("%")[1][
                :-1
            ]  # Remove trailing '0'
            badge_id = card_info.split("=")[1][1:]  # Remove leading '1'
            ts_str = datetime.now().__str__()

            # Ensure the CSV file exists
            if not os.path.exists(CSV_FILE_NAME):
                setup_csv_file()

            # Write to the CSV file
            with open(CSV_FILE_NAME, mode="a", encoding="UTF8") as f:
                writer = csv.writer(f)
                writer.writerow([penn_id, badge_id, card_info, ts_str])
    else:  # If not accepting swipes
        print("Not currently accepting swipes.")
        schedule.run_pending()
        time.sleep(config.swipe_timeout)
