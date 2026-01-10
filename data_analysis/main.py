from src.utils import project_paths, ensure_dir
from src.collect_git import collect_commits
from src.preprocess import preprocess
from src.analysis_basic import run_basic_analysis


def main():
    paths = project_paths()

    # ensure folders exist
    ensure_dir(paths["data_raw"])
    ensure_dir(paths["data_processed"])
    ensure_dir(paths["figures"])

    repo_path = str(paths["repo"])
    raw_csv = str(paths["data_raw"] / "commits_raw.csv")
    processed_csv = str(paths["data_processed"] / "commits.csv")
    stats_json = str(paths["data_processed"] / "basic_stats.json")

    print("Step 1/3: Collecting commit data...")
    collect_commits(repo_path=repo_path, output_csv=raw_csv)

    print("Step 2/3: Preprocessing data...")
    preprocess(raw_csv, processed_csv)

    print("Step 3/3: Running basic analysis & generating figures...")
    stats = run_basic_analysis(processed_csv, str(paths["figures"]), stats_out=stats_json)

    print("\nDone ✅")
    print(f"- Raw data: {raw_csv}")
    print(f"- Processed data: {processed_csv}")
    print(f"- Figures saved to: {paths['figures']}")
    print(f"- Stats JSON: {stats_json}")
    print("\nQuick summary:")
    for k, v in stats.items():
        if k in ["top_5_months_by_commits", "top_10_contributors", "commit_type_counts"]:
            continue
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
