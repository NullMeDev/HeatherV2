[x] 1. Install the required packages
[x] 2. Restart the workflow to see if the project is working
[x] 3. Verify the project is working using the feedback tool
[x] 4. Inform user the import is completed and they can start building, mark the import as completed using the complete_project_import tool

## Additional Improvements Made
[x] Created concurrent document queue system for tracking multiple uploaded documents
[x] Implemented parallel batch processing for multiple documents (up to 5 concurrent files, 15 concurrent cards per file)
[x] Added commands to manage concurrent document checks (/queue, /massall, /clearqueue, /stopall)
[x] Updated document handler to automatically queue files when uploaded