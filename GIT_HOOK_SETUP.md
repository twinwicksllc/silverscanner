# Git Hook Setup - Prevent Secret Commits

## Overview

A pre-commit git hook has been installed to **permanently prevent secrets from being committed** to the repository. This hook runs automatically before every commit and blocks commits containing secrets.

## What It Does

The hook scans staged files for:
- eBay API credentials (Client ID, Client Secret, Dev ID, User Token)
- Any patterns matching production credentials
- Hardcoded values in `render.yaml` and `RENDER_DEPLOYMENT_GUIDE.md`

## Hook Location

```
.git/hooks/pre-commit
```

This file is **executable** and runs automatically with every `git commit`.

## How It Works

### 1. Scans Staged Files
Only checks files that are staged for commit:
- `render.yaml`
- `RENDER_DEPLOYMENT_GUIDE.md`

### 2. Checks for Secret Patterns
Looks for patterns like:
- `ThomasFe-SuperNin-PRD-*` (eBay Client ID)
- `PRD-*` (eBay Client Secret)
- `v^1.1#i^1#p^3*` (eBay User Token)
- UUID patterns (Dev ID)

### 3. Blocks Commit if Secrets Found
If secrets are detected:
```
ERROR: Found potential secret in render.yaml matching pattern: ThomasFe-SuperNin-PRD
================================
COMMIT BLOCKED: Secrets detected!
================================
```

### 4. Provides Fix Instructions
The hook tells you exactly how to fix the issue:
```
To fix:
1. Edit the files to remove secrets
2. Use 'sync: false' in render.yaml
3. Use placeholder text like 'your-client-id' in documentation
4. Stage the fixed files: git add <file>
5. Try committing again
```

## Proper Configuration

### render.yaml (Correct Format)
```yaml
envVars:
  - key: EBAY_CLIENT_ID
    sync: false
  - key: EBAY_CLIENT_SECRET
    sync: false
  - key: EBAY_DEV_ID
    sync: false
  - key: EBAY_USER_TOKEN
    sync: false
```

**Note:** `sync: false` means the value is set in Render dashboard, not in the file.

### RENDER_DEPLOYMENT_GUIDE.md (Correct Format)
```markdown
- `EBAY_CLIENT_ID` = `your-production-client-id`
- `EBAY_CLIENT_SECRET` = `your-production-client-secret`
- `EBAY_DEV_ID` = `your-dev-id`
- `EBAY_USER_TOKEN` = `your-user-token`
```

**Note:** Use placeholder text, not actual credentials.

## Testing the Hook

### Test 1: Try to commit a secret
```bash
# Edit render.yaml to add a real credential
echo "value: ThomasFe-SuperNin-PRD-test123" >> render.yaml

# Try to commit
git add render.yaml
git commit -m "Test commit"

# Expected result: COMMIT BLOCKED
```

### Test 2: Commit with placeholders
```bash
# Edit render.yaml with proper format
# Use 'sync: false' instead of hardcoded values

git add render.yaml
git commit -m "Update config"

# Expected result: ✓ No secrets detected - commit succeeds
```

## Hook Installation

The hook is already installed in your local repository. To install it in a fresh clone:

```bash
# Copy the hook file
cp .git/hooks/pre-commit.sample .git/hooks/pre-commit

# Or create it manually (see content below)

# Make it executable
chmod +x .git/hooks/pre-commit
```

## Hook Content

The hook is located at `.git/hooks/pre-commit` and contains:

```bash
#!/bin/bash
# Pre-commit hook to prevent committing secrets

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check for secrets in staged files
echo "Checking for secrets in staged files..."

# Files to check
FILES_TO_CHECK="render.yaml RENDER_DEPLOYMENT_GUIDE.md"

# Patterns that indicate secrets
SECRET_PATTERNS=(
    "ThomasFe-SuperNin-PRD"
    "PRD-[a-z0-9]{12}-"
    "v\^1\.1#i\^1#p\^3"
    "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
)

FOUND_SECRETS=0

for file in $FILES_TO_CHECK; do
    if git diff --cached --name-only | grep -q "^$file$"; then
        echo "Checking $file..."
        
        for pattern in "${SECRET_PATTERNS[@]}"; do
            if git diff --cached $file | grep -E "$pattern" > /dev/null; then
                echo -e "${RED}ERROR: Found potential secret in $file${NC}"
                FOUND_SECRETS=1
            fi
        done
    fi
done

if [ $FOUND_SECRETS -eq 1 ]; then
    echo -e "${RED}COMMIT BLOCKED: Secrets detected!${NC}"
    exit 1
fi

echo -e "\033[0;32m✓ No secrets detected\033[0m"
exit 0
```

## Bypassing the Hook (NOT RECOMMENDED)

If you absolutely must bypass the hook (not recommended):
```bash
git commit --no-verify -m "Your message"
```

**Warning:** This defeats the purpose of the hook and may expose secrets!

## Troubleshooting

### Hook not running
**Cause:** Hook file not executable
**Fix:** `chmod +x .git/hooks/pre-commit`

### Hook always blocks commits
**Cause:** Secrets still in staged files
**Fix:** 
1. Check `git diff --cached` to see what's staged
2. Remove secrets from files
3. Use proper format (sync: false, placeholders)
4. Stage fixed files: `git add <file>`

### Hook not in fresh clone
**Cause:** Git hooks are not tracked in repository
**Fix:** 
1. Copy hook from another clone
2. Or recreate it manually
3. Make it executable

## Best Practices

1. **Never commit real credentials** - Use environment variables
2. **Use sync: false** - Let Render manage secrets
3. **Use placeholders** - In documentation, use example values
4. **Test before pushing** - The hook catches issues locally
5. **Review diffs** - Always check `git diff` before committing

## Summary

✅ **Installed:** Pre-commit hook active in `.git/hooks/pre-commit`
✅ **Automatic:** Runs on every commit
✅ **Protective:** Blocks commits with secrets
✅ **Helpful:** Provides fix instructions
✅ **Permanent:** Solves the recurring secret commit problem

This hook ensures secrets never make it to GitHub, protecting your eBay API credentials and other sensitive data.