"""
Layer 0: Kaggle Dataset Fetcher
도메인 전문가들의 데이터셋 자동 수집
"""

import os
import json
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import yaml


@dataclass
class KaggleDataset:
    """Kaggle 데이터셋 메타데이터"""
    owner: str
    name: str
    description: str
    update_frequency: str
    priority: int
    local_path: Optional[Path] = None
    last_updated: Optional[datetime] = None
    size_mb: Optional[float] = None


class KaggleFetcher:
    """
    Kaggle 데이터셋 자동 수집기

    Requirements:
        - kaggle CLI 설치: pip install kaggle
        - ~/.kaggle/kaggle.json 설정

    Usage:
        fetcher = KaggleFetcher("nba")
        fetcher.fetch_all()
        datasets = fetcher.list_local()
    """

    def __init__(self, sport: str, base_dir: Optional[Path] = None):
        """
        Args:
            sport: 스포츠 코드 (nba, nfl, mlb, etc.)
            base_dir: 데이터 저장 기본 디렉토리
        """
        self.sport = sport
        self.base_dir = base_dir or Path(f"/Users/js/g9/g9_sports_platform/data/{sport}/kaggle")
        self.config = self._load_config()

        # 디렉토리 생성
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _load_config(self) -> Dict[str, Any]:
        """스포츠별 Kaggle 설정 로드"""
        config_path = Path(f"/Users/js/g9/g9_sports_platform/sports/{self.sport}/config.yaml")

        with open(config_path, 'r', encoding='utf-8') as f:
            full_config = yaml.safe_load(f)

        return full_config.get('layer0_experts', {}).get('kaggle', {})

    def get_datasets(self) -> List[KaggleDataset]:
        """설정된 데이터셋 목록 반환"""
        datasets = []

        for ds_config in self.config.get('datasets', []):
            datasets.append(KaggleDataset(
                owner=ds_config['owner'],
                name=ds_config['name'],
                description=ds_config.get('description', ''),
                update_frequency=ds_config.get('update_frequency', 'unknown'),
                priority=ds_config.get('priority', 3)
            ))

        # 우선순위 순 정렬
        return sorted(datasets, key=lambda x: x.priority)

    def fetch_dataset(self, dataset: KaggleDataset, force: bool = False) -> Path:
        """
        단일 데이터셋 다운로드

        Args:
            dataset: KaggleDataset 객체
            force: True면 기존 파일 덮어쓰기

        Returns:
            다운로드된 데이터셋 경로
        """
        dataset_id = f"{dataset.owner}/{dataset.name}"
        target_dir = self.base_dir / dataset.name

        # 이미 존재하고 force가 아니면 스킵
        if target_dir.exists() and not force:
            print(f"[Kaggle] {dataset_id} already exists, skipping...")
            return target_dir

        print(f"[Kaggle] Downloading {dataset_id}...")

        try:
            # kaggle CLI로 다운로드
            cmd = [
                "kaggle", "datasets", "download",
                "-d", dataset_id,
                "-p", str(target_dir),
                "--unzip"
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5분 타임아웃
            )

            if result.returncode != 0:
                print(f"[Kaggle] Error: {result.stderr}")
                raise RuntimeError(f"Kaggle download failed: {result.stderr}")

            print(f"[Kaggle] Downloaded to {target_dir}")

            # 메타데이터 저장
            self._save_metadata(dataset, target_dir)

            return target_dir

        except subprocess.TimeoutExpired:
            print(f"[Kaggle] Timeout downloading {dataset_id}")
            raise

    def fetch_all(self, force: bool = False) -> Dict[str, Path]:
        """
        모든 설정된 데이터셋 다운로드

        Returns:
            {dataset_name: local_path} 딕셔너리
        """
        results = {}
        datasets = self.get_datasets()

        print(f"[Kaggle] Fetching {len(datasets)} datasets for {self.sport.upper()}...")

        for dataset in datasets:
            try:
                path = self.fetch_dataset(dataset, force)
                results[dataset.name] = path
            except Exception as e:
                print(f"[Kaggle] Failed to fetch {dataset.name}: {e}")
                results[dataset.name] = None

        return results

    def _save_metadata(self, dataset: KaggleDataset, target_dir: Path):
        """데이터셋 메타데이터 저장"""
        metadata = {
            "owner": dataset.owner,
            "name": dataset.name,
            "description": dataset.description,
            "update_frequency": dataset.update_frequency,
            "priority": dataset.priority,
            "downloaded_at": datetime.now().isoformat(),
            "sport": self.sport
        }

        metadata_path = target_dir / "_metadata.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

    def list_local(self) -> List[Dict[str, Any]]:
        """로컬에 다운로드된 데이터셋 목록"""
        datasets = []

        if not self.base_dir.exists():
            return datasets

        for item in self.base_dir.iterdir():
            if item.is_dir():
                metadata_path = item / "_metadata.json"
                if metadata_path.exists():
                    with open(metadata_path, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                        metadata['local_path'] = str(item)
                        metadata['files'] = [f.name for f in item.iterdir() if f.is_file() and f.name != '_metadata.json']
                        datasets.append(metadata)

        return datasets

    def get_dataset_files(self, dataset_name: str) -> List[Path]:
        """특정 데이터셋의 파일 목록"""
        target_dir = self.base_dir / dataset_name

        if not target_dir.exists():
            return []

        return [
            f for f in target_dir.iterdir()
            if f.is_file() and not f.name.startswith('_')
        ]

    def search_kaggle(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Kaggle에서 데이터셋 검색

        Args:
            query: 검색어
            max_results: 최대 결과 수

        Returns:
            검색 결과 리스트
        """
        try:
            cmd = [
                "kaggle", "datasets", "list",
                "-s", query,
                "--csv"
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                print(f"[Kaggle] Search error: {result.stderr}")
                return []

            # CSV 파싱
            lines = result.stdout.strip().split('\n')
            if len(lines) < 2:
                return []

            headers = lines[0].split(',')
            datasets = []

            for line in lines[1:max_results + 1]:
                values = line.split(',')
                if len(values) >= len(headers):
                    datasets.append(dict(zip(headers, values)))

            return datasets

        except Exception as e:
            print(f"[Kaggle] Search failed: {e}")
            return []


# CLI 인터페이스
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Kaggle Dataset Fetcher")
    parser.add_argument("sport", help="Sport code (nba, nfl, mlb, etc.)")
    parser.add_argument("--fetch", action="store_true", help="Fetch all configured datasets")
    parser.add_argument("--list", action="store_true", help="List local datasets")
    parser.add_argument("--search", type=str, help="Search Kaggle for datasets")
    parser.add_argument("--force", action="store_true", help="Force re-download")

    args = parser.parse_args()

    fetcher = KaggleFetcher(args.sport)

    if args.fetch:
        results = fetcher.fetch_all(force=args.force)
        print(f"\n[Result] Downloaded {len([r for r in results.values() if r])} datasets")

    elif args.list:
        datasets = fetcher.list_local()
        print(f"\n[Local] {len(datasets)} datasets:")
        for ds in datasets:
            print(f"  - {ds['name']}: {len(ds.get('files', []))} files")

    elif args.search:
        results = fetcher.search_kaggle(args.search)
        print(f"\n[Search] {len(results)} results:")
        for ds in results:
            print(f"  - {ds.get('ref', 'N/A')}")

    else:
        parser.print_help()
