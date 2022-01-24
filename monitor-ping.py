import csv
import os
import sys
import signal
import time
import datetime
from os.path import exists

# threshold for lag in ms
lag_threshold = 100
hostname = "google.com"
ping_headers = ["Start Time", "End Time", "Duration", "Average", "Start Time (ns)", "End Time (ns)"]


def init():
    global currently_lagging
    currently_lagging = False

    global lag_start_time
    lag_start_time = None

    global lag_entries
    lag_entries = 0

    global lag_total
    lag_total = 0

    global ping_records
    ping_records = []

    global current_date
    current_date = get_current_date()

def signal_handler(sig, frame):
    write_records()
    sys.exit(0)


def get_ping():
    response = os.popen("ping -q -c 1 " + hostname).read()
    response_line = response.strip().split("\n")[-1]
    ping_blocks = response_line.split(" ")[3]
    return float(ping_blocks.split("/")[0])


def get_current_date():
    return datetime.date.today().strftime("%B_%d_%Y")


def capture_range():
    global currently_lagging
    global lag_start_time
    global lag_total
    global lag_entries

    if currently_lagging:
        if lag_entries >= 8:
            end_time = datetime.datetime.now()
            # was lagging, and now is not
            ping_records.append([
                lag_start_time.strftime("%H:%M:%S"),
                end_time.strftime("%H:%M:%S"),
                str(int((end_time - lag_start_time).total_seconds())) + " seconds",
                str(int(lag_total / lag_entries)) + " ms",
                lag_start_time.timestamp(),
                end_time.timestamp()
            ])

        lag_start_time = None
        lag_entries = 0
        lag_total = 0
        currently_lagging = False


def write_records():
    global cumulative_time

    capture_range()
    filename = "ping_record_" + current_date
    file_exists = exists(filename)

    with open(filename, 'a+') as csv_file:
        if not file_exists:
            # reset total count
            csv_file.write(",".join(map(str, ping_headers)) + "\n")

        for record in ping_records:
            csv_file.write(",".join(map(str, record)) + "\n")

        if current_date != get_current_date():
            # If this is the last write for this file, record the cumulative total
            csv_file.write("Cumulative total: " + str(round(cumulative_time / 60, 2)) + "\n")

    init()


if __name__ == "__main__":
    global currently_lagging
    global lag_start_time
    global lag_entries
    global lag_total
    global ping_records
    global current_date
    global cumulative_time
    cumulative_time = 0

    signal.signal(signal.SIGINT, signal_handler)

    init()

    while True:
        if current_date != get_current_date():
            write_records()
            cumulative_time = 0

        try:
            ping = get_ping()
        except Exception as e:
            print(e)
            # If there is an exception, it is likely that
            ping = 1000

        if ping > lag_threshold:
            if not currently_lagging:
                currently_lagging = True
                # Wasn't lagging, and now is
                lag_start_time = datetime.datetime.now()

                print("Lag start " + lag_start_time.strftime("%H:%M:%S"))

            lag_entries += 1
            lag_total += ping
            cumulative_time += 1
        elif ping < lag_threshold and currently_lagging:
            write_records()
            print("Lag end " + datetime.datetime.now().strftime("%H:%M:%S") + " [" + str(round(cumulative_time / 60, 2)) + "]")

        try:
            time.sleep(1)
        except:
            signal_handler(None, None)
