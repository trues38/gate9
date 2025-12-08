from guardian.pipeline import process_raw_event
from cleaner.pipeline import run_cleaning_job

def full_ingest_flow():
    # 1) RSS/Youtube/SNS 등 입력 수집 → events 테이블 저장
    process_raw_event()

    # 2) Clean → events_cleaned
    run_cleaning_job()