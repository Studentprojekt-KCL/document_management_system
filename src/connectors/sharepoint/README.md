The following needs to be exported in local environment:

    CONSHAREPOINT_BIND_ADDR=<BIND_ADDRESS>
    CONSHAREPOINT_BIND_PORT=<CONNECTOR_PORT>
    CONSHAREPOINT_SYSTEM_NAME=<Name to display in frontend for this SharePoint instance (e.g. 'SharePoint')>
    CONSHAREPOINT_TENANT_ID=<Azure AD tenant ID — found in Azure portal: Entra ID → Overview>
    CONSHAREPOINT_CLIENT_ID=<Client ID of DMIS application registered in Azure AD>
    CONSHAREPOINT_CLIENT_SECRET=<Client secret of DMIS application in Azure AD>
    CONSHAREPOINT_STATE_SIGNING_SECRET=<Secret string used for OAuth state signing>

# Azure AD App Registration

Register an app in portal.azure.com (Entra ID → App registrations) with:
- Delegated API permissions: Sites.Read.All, Files.Read.All, offline_access
- Redirect URI pointing to: http(s)://<connector-host>/callback

# Response structure

## Endpoint: /get_files

    {
        "unique_pointer": <GRAPH API URL TO ITEM>,
        "name": "<FILE NAME>",
        "size": 1024,
        "last_edit_date": <ISO EDIT DATE>,
        "type": "source_file",
        "source_system": "SharePoint",
        "clickable_url": <WEB URL TO FILE>,
        "file_type": ".pdf",
        "file_type_description": "PDF"
    }

## Endpoint: /stream_files_to_index

First line: {"subdata": "<base64-encoded delta token map>"}
Subsequent lines (one per qualifying document):

    {
        "content": null,
        "metadata": {
            "unique_pointer": <GRAPH API URL TO ITEM>,
            "name": "<FILE NAME>",
            "size": 1024,
            "last_edit_date": <ISO EDIT DATE>,
            "type": "source_file",
            "source_system": "SharePoint",
            "clickable_url": <WEB URL TO FILE>,
            "file_type": ".pdf",
            "file_type_description": "PDF"
        }
    }
