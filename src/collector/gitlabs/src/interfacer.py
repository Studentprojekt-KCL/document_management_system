import os
from urllib.parse import urljoin
import base64

import requests

from unpacker import unpack_values
from logger import dms_error, dms_info

from hashlib import md5

from variables import PROJECT, SOURCE_FILE

class GitLabs:
    API_URL: str = "api/v4/"
    GIT_BLAME: str = "blame?ref=HEAD"
    GIT_HEAD: str = "?ref=HEAD"

    def __init__(self):
        """Constructor."""
        address = os.environ.get("GITLAB_ADDRESS")
        self.base = urljoin(address, self.API_URL)

    def _get_projects(self) -> dict:
        url = urljoin(self.base, "projects")
        return self._execute_request(url)

    def get_project_ids(self) -> dict[int, str]:
        ids: dict[int, str] = {}
        for project in self._get_projects():
            hash_object = md5(project.get("last_activity_at").encode()).hexdigest()
            ids[project.get("id")] = hash_object

        return ids

    def get_projects_as_units(self):
        content = self._get_projects()

        projects: dict = {}
        for project in content:
            projects[project.get("web_url")] = {"name": unpack_values(project, ("name",)),
                        "creator": unpack_values(project, ("namespace", "name")),
                        "created_date": unpack_values(project, ("created_at",)),
                        "last_edit_date": unpack_values(project, ("last_activity_at",)),
                        "type": PROJECT
                        }

        return projects

    def get_files_in_project(self, project_id: int) -> list:
        """Retrieve URLs for all available files in a project.
        
        Args:
        ----
            project_id: Gitlabs integer value for a specific project.
        """
        tree_args: str = f"projects/{project_id}/repository/tree?recursive=true&per_page=100&pagination=none"
        url = urljoin(self.base, tree_args)
        content = self._execute_request(url)
        base_path = urljoin(self.base, f"projects/{project_id}/repository/files/")
        return [urljoin(base_path, file.get("path").replace("/", "%2F")) for file in content]

    def get_file(self, url: str, include_content: bool = True) -> dict:
        """
        
        Args:
        ----
            URL: The URL should be given formatted like:
              https://<GITLABS_DOMAIN>/api/v4/projects/<PROJECT_ID>/repository/files/<FILE_PATH>
            include_content: Determine if actual file content should be included or not.

        """
        file = self._execute_request(urljoin(url, self.GIT_HEAD))
        blame = self._execute_request(urljoin(url.rstrip('/') + '/', self.GIT_BLAME))

        base_structure = {"metadata": {
                "unique_pointer": url,
                "name": file.get("file_name"),
                "size": file.get("size"),
                "last_edit_date": unpack_values(blame, [0, "commit", "committed_date"]),
                "type": SOURCE_FILE
                }
            }

        if include_content:
            base_structure |= {"content": file.get("content")}

        return base_structure

    def pointers_to_all_files_to_index(self, subdata: dict | None) -> list:
        """Retrieve a containing URLs pointing to all available individual files available, except those in projects 
            already indexed according to subdata.

        Args:
        ----
            subdata: Data structured: {<Project_ID>: md5(timestamp)} (this data should not be of concern at other layers of the system, 
                but should always be supplied).
        """
        if subdata is None:
            subdata = {}

        file_pointers: list = []
        for project_id, change_hash in self.get_project_ids().items():
            if change_hash == subdata.get(project_id):
                continue
            file_pointers.extend(self.get_files_in_project(project_id))

        return file_pointers

    @staticmethod
    def _execute_request(url: str) -> dict | list:
        """Execute request to supplied URL, JSON content in response expected."""
        try:
            response = requests.get(url)
            content = response.json()
        except requests.exceptions.JSONDecodeError:
            dms_error(f"Gitlab request to {url} could not be decoded.\nExpected JSON structure\nGot {content}")
            return {}
        if response.status_code != 200:
            dms_info(f"Request to {url} was made. However, Gitlabs provided a {response.status_code} response.")
        return content


if __name__ == "__main__":
    i = GitLabs()
    url = "https://gitlab.dms-lookup.com/api/v4/projects/2/repository/files/CODE_OF_CONDUCT.md"
    url = "https://gitlab.dms-lookup.com/api/v4/projects/3/repository/files/windows%2FINSTALL-MinGW-w64_with_CMake.txt"
    print(i.pointers_to_all_files_to_index({3: '4726e885661ba1e0875106c1a92b338a'}))



# So, a smart archetecture is probabaly that we can deliver some 'indexing' data from the collectors up to the SE, which only is intended to pass back. And this data in turn should be passed back
# so that we know if we do need to reindex project or not (while this abstraction isn't known by the SE)

# PASSED information_container => somehow encoded to contain latest project checksums => if project changed -> reindex.
