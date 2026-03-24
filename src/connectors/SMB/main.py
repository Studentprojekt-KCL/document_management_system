""" import os
from smb import SMBCollector


def print_results(title, result):
    print(f"\n=== {title} ===")
    print(f"Files returned: {len(result.get('files', []))}")
    print(f"Deleted files: {len(result.get('deleted', []))}")

    if result.get("files"):
        print("\nChanged / Added / Modified files:")
        for f in result["files"]:
            print(f" + {f['metadata']['unique_pointer']}")

    if result.get("deleted"):
        print("\nDeleted files:")
        for f in result["deleted"]:
            print(f" - {f}")


def main():
    collector = SMBCollector()

    print("=== SMB COLLECTOR INCREMENTAL TEST ===\n")

    # ----------------------------
    # 0. Check mount
    # ----------------------------
    if not os.path.exists(collector.BASE_PATH):
        print(f" ERROR: {collector.BASE_PATH} not found")
        print("Mount SMB first!")
        return

    print(f" SMB path OK: {collector.BASE_PATH}")

    # ----------------------------
    # 1. FIRST RUN
    # ----------------------------
    print("\nRunning FIRST scan...")
    result1 = collector.files_to_index()

    print_results("FIRST RUN", result1)

    subdata = result1["subdata"]

    # ----------------------------
    # 2. WAIT FOR USER CHANGES
    # ----------------------------
    print("\n Now MODIFY the SMB files manually:")
    print(" - Add a file")
    print(" - Modify a file")
    print(" - Delete a file")

    input("\nPress ENTER when ready to run SECOND scan...")

    # ----------------------------
    # 3. SECOND RUN
    # ----------------------------
    print("\nRunning SECOND scan...")
    result2 = collector.files_to_index(subdata)

    print_results("SECOND RUN", result2)

    # ----------------------------
    # 4. DONE
    # ----------------------------
    print("\n TEST COMPLETE")


if __name__ == "__main__":
    main()
 """