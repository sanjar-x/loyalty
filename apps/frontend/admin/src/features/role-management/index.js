// User-facing actions for IAM: list/edit/delete roles + assign their
// permission sets. The plain entity (`entities/role`) only models the
// data + CRUD wrappers — anything that drives a tab page or an
// open-the-edit-modal flow lives here.
export { RolesTab } from './ui/RolesTab';
export { PermissionsTab } from './ui/PermissionsTab';
