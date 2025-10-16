import os
import sys
from typing import *
from loguru import logger
from configparser import ConfigParser
from datetime import datetime, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build

path_this = os.path.dirname(os.path.abspath(__file__))
path_project = os.path.dirname(os.path.join(path_this, ".."))
path_root = os.path.dirname(os.path.join(path_this, "../.."))
sys.path.extend([path_root, path_project, path_this])

from tools import BaseTaskManagement

class SpreadsheetTool(BaseTaskManagement):
    """
    Tool for managing task records in a Google Spreadsheet.

    This class provides functionality to append multiple rows of task data
    into a specific Google Spreadsheet. Each task entry contains metadata 
    such as timestamp, user name, project details, task information, 
    start date, assignor, and status.

    The class uses Google Sheets API with service account authentication.
    """

    config: ClassVar[ConfigParser] = ConfigParser()
    config.read(os.path.join(path_root, "config.conf"))

    SPREADSHEET_ID: ClassVar[str] = "1ERtqh9-4-gX1qQoIh9rcecnt2JvJN5GLJZQcteBEAYg"
    SERVICE_ACCOUNT_FILE: ClassVar[str] = config["default"]["spreadsheet_path"]
    SCOPES: ClassVar[List[str]] = ["https://www.googleapis.com/auth/spreadsheets"]

    async def input_task_management(
            self, 
            name: List[str],
            project_name: List[str], 
            task: List[str],
            sub_task: List[str],
            assignor: List[str]
        ):
        """
        Append multiple task entries to the Google Spreadsheet.

        Args:
            name (List[str]): List of assignee names.
            project_name (List[str]): List of project names associated with each task.
            task (List[str]): List of main task descriptions.
            sub_task (List[str]): List of sub-task descriptions.
            start_date (List[str]): List of task start dates (as strings).
            assignor (List[str]): List of assignor names for each task.

        Returns:
            str: A success message indicating how many tasks were added.

        Raises:
            ValueError: If the length of input lists do not match.
            Exception: For errors during Google Sheets API operations.
        """
        def datetime_to_serial(date: datetime) -> float:
            """
            Convert Python datetime to Google Sheets serial number format.
            """
            epoch = datetime(1899, 12, 30)
            delta = date - epoch
            return delta.days + (delta.seconds / 86400) + (delta.microseconds / 86400_000000)
        
        logger.info("Attempting to append multiple tasks to spreadsheet")

        total_tasks = len(name)
        if not all(
            len(lst) == total_tasks
            for lst in [project_name, task, sub_task, assignor]
        ):
            raise ValueError("❌ All input lists must have the same length")
        
        creds = service_account.Credentials.from_service_account_file(
            self.SERVICE_ACCOUNT_FILE, scopes=self.SCOPES
        )
        service = build("sheets", "v4", credentials=creds)
        range_ = "Recap Task Agent!A:N"

        values = []
        for i in range(total_tasks):
            row = [
                datetime_to_serial(datetime.now()),            # timestamp
                name[i],                                       # assignee
                "Fakhri",                                      # fixed field (can be dynamic)
                project_name[i],                               # project name
                task[i],                                       # main task
                sub_task[i],                                   # sub task
                None,                                          # placeholder
                datetime_to_serial(datetime.now()),            # start date
                None,                                          # placeholder
                None,                                          # placeholder
                assignor[i],                                   # assignor
                "PIC",                                         # role
                "on progress",                                 # status
                name[i],                                       # reference to assignee
            ]
            values.append(row)

        body = {"values": values}
        result = service.spreadsheets().values().append(
            spreadsheetId=self.SPREADSHEET_ID,
            range=range_,
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body=body
        ).execute()

        logger.info(f"{total_tasks} task(s) successfully appended to spreadsheet")
        return f"✅ Task berhasil ditambahkan untuk detailnya bisa di cek di link spreadsheet berikut:\nhttps://docs.google.com/spreadsheets/d/1ERtqh9-4-gX1qQoIh9rcecnt2JvJN5GLJZQcteBEAYg/edit?gid=2142894050#gid=2142894050"
    
    async def get_undone_task(self, name: str) -> str:
        """
        Retrieve undone tasks for a given user from the Google Spreadsheet
        and return a formatted string.

        Args:
            name (str): The name of the assignee whose tasks should be checked.

        Returns:
            str: A message indicating whether undone tasks exist.
                Includes a formatted list of tasks if available.
        """
        logger.info(f"Fetching undone tasks for user: {name}")
        creds = service_account.Credentials.from_service_account_file(
            self.SERVICE_ACCOUNT_FILE, scopes=self.SCOPES
        )
        service = build("sheets", "v4", credentials=creds)

        range_ = "Recap Task Agent!A:N"
        result = service.spreadsheets().values().get(
            spreadsheetId=self.SPREADSHEET_ID,
            range=range_
        ).execute()

        values = result.get("values", [])

        if not values:
            logger.warning("No data found in the spreadsheet")
            return f"❌ Tidak ada data pada spreadsheet."

        undone_tasks = [
            row for row in values
            if len(row) >= 6
            and row[1].strip().lower() == name.strip().lower()
            and row[12].strip().lower() != "done"
        ]

        if not undone_tasks:
            return f"✅ Tidak ada task yang belum selesai dari {name}.\n\nKEEP IT THE GOOD WORK 👍"

        # Format daftar task
        task_list = "\n".join(
            f"- {row[3]} | {row[5]} | {row[10]}"
            for row in undone_tasks
        )

        return (
            f"📌 Terdapat {len(undone_tasks)} task yang belum selesai dari {name}:\n\n"
            f"{task_list}"
        )
    
    async def update_task_status(
            self, 
            name: str, 
            sub_tasks: List[str], 
            status: str = "done"
        ) -> str:
        """
        Update the status of tasks for a given user.

        Args:
            name (str): The assignee's name.
            sub_task List(str): The sub-tasks description to match.
            status (str): The new status to set (default: "done").

        Returns:
            str: A message confirming the update.
        """
        def datetime_to_serial(date: datetime) -> float:
            """
            Convert Python datetime to Google Sheets serial number format.
            """
            epoch = datetime(1899, 12, 30)
            delta = date - epoch
            return delta.days + (delta.seconds / 86400) + (delta.microseconds / 86400_000000)
        
        def parse_gsheet_datetime(value: str) -> datetime:
            """Parse Google Sheets datetime (serial or string) to Python datetime."""
            try:
                # Kalau value berupa serial number (float)
                serial = float(value)
                return datetime(1899, 12, 30) + timedelta(days=serial)
            except ValueError:
                # Kalau value berupa string tanggal
                try:
                    return datetime.strptime(value, "%m/%d/%Y %H:%M:%S")
                except ValueError:
                    try:
                        return datetime.strptime(value, "%m/%d/%Y")
                    except ValueError:
                        return datetime.now()
        
        logger.info(f"Updating task status for {name} - {', '.join(sub_tasks)} → {status}")

        creds = service_account.Credentials.from_service_account_file(
            self.SERVICE_ACCOUNT_FILE, scopes=self.SCOPES
        )
        service = build("sheets", "v4", credentials=creds)

        range_ = "Recap Task Agent!A:N"
        result = service.spreadsheets().values().get(
            spreadsheetId=self.SPREADSHEET_ID,
            range=range_
        ).execute()

        values = result.get("values", [])

        if not values:
            return "❌ Spreadsheet kosong."
        
        updates = []
        updated_tasks = []
        for idx, row in enumerate(values, start=1):
            if (
                len(row) >= 13
                and row[1].strip().lower() == name.strip().lower()
                and row[12].strip().lower() != "done"
                and any(sub.strip().lower() in row[5].strip().lower() for sub in sub_tasks)
            ):
                start_date = parse_gsheet_datetime(row[7])
                end_date = datetime.now()
                duration_minutes = int((end_date - start_date).total_seconds() / 60)

                end_date_serial = datetime_to_serial(end_date)

                updates.append({
                    "range": f"Recap Task Agent!I{idx}:M{idx}", 
                    "values": [[end_date_serial, duration_minutes, row[10], row[11], status]]
                })
                updated_tasks.append(row[5])
        
        if updates:
            body = {"valueInputOption": "RAW", "data": updates}
            service.spreadsheets().values().batchUpdate(
                spreadsheetId=self.SPREADSHEET_ID,
                body=body
            ).execute()
            return f"✅ {len(updated_tasks)} task milik {name} berhasil diupdate → {', '.join(updated_tasks)}"
        
        return f"⚠️ Tidak ada task dari {name} yang cocok."