"""Configuration variables for SMB connector operations."""

PROJECT = "project"
SOURCE_FILE = "source_file"
BASE_PATH = "/smb/Kernel/projB/"
MAX_FILE_SIZE = 5_000_000  # 5 MB limit
ALLOWED_EXTENSIONS = (".txt", ".md", ".xml", ".pdf", ".docx", ".xlsx")
SKIP_DIRS = {"drivers", ".git"}
