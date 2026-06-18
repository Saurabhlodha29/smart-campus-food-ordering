import { create } from "zustand";
import { persist } from "zustand/middleware";

const emptyAuth = {
  token: null,
  role: null,
  userId: null,
  userName: null,
  userEmail: null,
  campusId: null,
  campusName: null,
  accountStatus: null,
  pendingPenalty: 0,
};

export const normalizeAuth = (data) => ({
  token: data.token,
  role: String(data.role || "").replace("ROLE_", "").toUpperCase(),
  userId: data.id ? Number(data.id) : null,
  userName: data.name || null,
  userEmail: data.email || null,
  campusId: data.campusId ? Number(data.campusId) : null,
  campusName: data.campusName || null,
  accountStatus: data.accountStatus || null,
  pendingPenalty: Number(data.pendingPenalty || 0),
});

export const useAuthStore = create(
  persist(
    (set) => ({
      ...emptyAuth,
      setAuth: (data) => set(normalizeAuth(data)),
      clearAuth: () => set(emptyAuth),
    }),
    { name: "scf_auth" },
  ),
);
