Items in the chat form of a release of format 2.0 or lower; in format 2.1 or higher the filled items are the item files in `v1.0.x/owner/queue/`.

# Item examples

One real item, written in each variant of [../templates/item.md](../templates/item.md).

## Default

```Markdown
# Q139. The app gets a super admin role. The first account is the super admin.
- Role seed code: `RbacService.onModuleInit`, both backends. Runs at backend start.
- Set-up request: creates the first account.
## Options:
1. Recommended: add the role
   - Update role seed code:
     - Super admin, rank 0.
     - Admin, rank 1.
     - User, rank 20.
   - Update set-up request: first account gets Super admin.
   - After merge, the lead deletes the owner's local database of this project and creates it again.

**Say:**
- A. `record it`: record.
- B. `iterate`: record and start now.
```

## With a `Now` group: the current behavior matters for the decision

```Markdown
# Q139. The app gets a super admin role. The first account is the super admin.
- Now
  - Role seed code, `RbacService.onModuleInit`, both backends. Runs at backend start.
    - Admin, rank 0.
    - User, rank 20.
  - Set-up request: first account gets Admin.
## Options:
1. Recommended: add the role
   - Update role seed code:
     - Super admin, rank 0.
     - Admin, rank 1.
     - User, rank 20.
   - Update set-up request: first account gets Super admin.
   - After merge, the lead deletes the owner's local database of this project and creates it again.

**Say:**
- A. `record it`: record.
- B. `iterate`: record and start now.
```

## With two options

```Markdown
# Q139. The app gets a super admin role. The first account is the super admin.
- Now
  - Role seed code, `RbacService.onModuleInit`, both backends: Admin (rank 0), User (rank 20).
  - Set-up request: first account gets Admin.
## Options:
1. Recommended: add the role, create the local database again
   - Update role seed code: Super admin (rank 0), Admin (rank 1), User (rank 20).
   - Update set-up request: first account gets Super admin.
   - After merge, the lead deletes the owner's local database of this project and creates it again.
2. Add the role, keep the local database
   - Same code changes as 1.
   - After merge, the lead changes two values by hand:
     - Admin role: rank 0 to 1.
     - Owner's dev account: Admin to Super admin.

**Say:**
- A. `record it`: record.
- B. `iterate`: record and start now.
```
