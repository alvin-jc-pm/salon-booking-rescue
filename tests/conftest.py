import os
import tempfile

# The prototype writes salon.db into the current folder when it is imported.
# Run the tests from a throwaway folder so they never touch a real database.
os.chdir(tempfile.mkdtemp(prefix="salon-tests-"))
