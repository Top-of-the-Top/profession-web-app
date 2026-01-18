import { tokenStorage } from './storage';

export function isAuthenticated(): boolean {
	console.log(tokenStorage.get())
  return Boolean(tokenStorage.get());
}
