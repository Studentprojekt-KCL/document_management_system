# useSearchMetadata

* resolveFilename
  * Extracts filename from different structures (metadata.name, direct name)
  * Handles missing, empty, or whitespace-only values
  * Generates fallback names (result-{index})

* resolveDocumentType
  * Detects document type based on file extension or sourceType
  * Supports PDF, Word, Excel, Text, and Markdown
  * Case-insensitive matching
  * Graceful fallback when no match is found

* resolveSource
  * Extracts source system from metadata or root object
  * Handles missing or null values

* resolveDateOnly
  * Extracts date (YYYY-MM-DD) from ISO timestamps
  * Handles timezone formats and plain dates
  * Returns empty string if unavailable

* resolveLink
  * Extracts clickable URLs from metadata or root level
  * Handles missing or null inputs

* resolveSecurityClass
  * Extracts document classification (e.g., Public, Confidential)
  * Handles missing values safely

# useFilters

## useSourceFilters

* Starts as empty array
* Calls the correct endpoint
* Populates with fetched data
* Stays empty on failed response
* Stays empty on network error
* Creates a new ref per call (not shared)

## useSecurityFilters

* Same six scenarios as above
* Plus: verifies the exact error messages logged on failure
* Plus: confirms each call creates an independent ref (this is actually a limitation worth knowing — it means two components calling useSecurityFilters() will each make their own API call)
