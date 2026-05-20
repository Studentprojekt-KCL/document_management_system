# System documentation

## Security implementations

### Changing security classifications

Only a user in the defined admin group DMISAPI_ADMIN_ROLES, can update security classifications.

### Rate limiting
<JEPPE>

### Input validation rules

#### Basic authentication input

All service connection using user supplied authentication is validated to have format "<USERNAME>:<PASSWORD>", where this string is validated. Any UTF-8 character is supported for username and password.
