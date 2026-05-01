import { usersSeed } from '@/shared/mocks/users';

const users = [...usersSeed];

export function getUsers() {
  return [...users];
}

export function getUserById(id) {
  return users.find((u) => u.id === id) ?? null;
}
