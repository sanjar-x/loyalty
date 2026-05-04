// TanStack Query key factories — see https://tkdodo.eu/blog/effective-react-query-keys.
export const staffKeys = {
  all: ['staff'],
  lists: () => [...staffKeys.all, 'list'],
  list: (filters) => [...staffKeys.lists(), filters],
  details: () => [...staffKeys.all, 'detail'],
  detail: (identityId) => [...staffKeys.details(), identityId],
};

export const invitationKeys = {
  all: ['staff-invitations'],
  lists: () => [...invitationKeys.all, 'list'],
  list: (filters) => [...invitationKeys.lists(), filters],
};
