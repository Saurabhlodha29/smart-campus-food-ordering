import { create } from "zustand";
import { persist } from "zustand/middleware";

export const useAuthStore = create(
  persist(
    (set) => ({
      token: null,
      role: null,
      userId: null,
      userName: null,
      userEmail: null,
      campusId: null,
      accountStatus: null,
      pendingPenalty: 0,
      setAuth: (data) => set(data),
      clearAuth: () =>
        set({
          token: null, role: null, userId: null, userName: null,
          userEmail: null, campusId: null, accountStatus: null, pendingPenalty: 0,
        }),
    }),
    { name: "scf_auth" }
  )
);
