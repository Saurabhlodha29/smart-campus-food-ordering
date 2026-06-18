import { useMutation } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { useNavigate } from "react-router-dom";
import { login, register, resendOtp, verifyEmail } from "../api/auth";
import { apiErrorMessage } from "../api/client";
import { homeForRole } from "../utils/roleRouting";
import { useAuthStore } from "../store/authStore";

export function useAuth() {
  const navigate = useNavigate();
  const setAuth = useAuthStore((state) => state.setAuth);
  const clearAuth = useAuthStore((state) => state.clearAuth);

  const finishAuth = (data) => {
    setAuth(data);
    toast.success(`Welcome, ${data.name || "back"}!`);
    navigate(homeForRole(data.role), { replace: true });
  };

  const loginMutation = useMutation({ mutationFn: login, onSuccess: finishAuth, onError: (e) => toast.error(apiErrorMessage(e)) });
  const registerMutation = useMutation({ mutationFn: register, onSuccess: (data) => toast.success(data.message), onError: (e) => toast.error(apiErrorMessage(e)) });
  const verifyMutation = useMutation({ mutationFn: verifyEmail, onSuccess: finishAuth, onError: (e) => toast.error(apiErrorMessage(e)) });
  const resendMutation = useMutation({ mutationFn: resendOtp, onSuccess: (data) => toast.success(data.message), onError: (e) => toast.error(apiErrorMessage(e)) });

  return {
    login: loginMutation,
    register: registerMutation,
    verify: verifyMutation,
    resend: resendMutation,
    logout: () => { clearAuth(); navigate("/login", { replace: true }); },
  };
}
