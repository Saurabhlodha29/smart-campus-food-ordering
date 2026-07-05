import client from "./client";
import { API } from "../constants/api-endpoints";

export const applyAdmin = async (payload) => (await client.post(API.APPLY_ADMIN, payload)).data;
export const applyOutlet = async (payload) => (await client.post(API.APPLY_OUTLET, payload)).data;
export const getOutletApplications = async () => (await client.get(API.OUTLET_APPLICATIONS)).data;
export const reviewOutletApplication = async ({ id, approved, ...payload }) =>
  (await client.patch(approved ? API.OUTLET_APPLICATION_APPROVE(id) : API.OUTLET_APPLICATION_REJECT(id), payload)).data;
export const getAdminApplications = async () => (await client.get(API.ADMIN_APPLICATIONS)).data;
export const getAllOutletApplications = async () => (await client.get(API.OUTLET_APPLICATIONS_ALL)).data;
export const sendAdminOtp = async (payload) => (await client.post(API.ADMIN_APP_SEND_OTP, payload)).data;
export const verifyAdminOtp = async (payload) => (await client.post(API.ADMIN_APP_VERIFY_OTP, payload)).data;
export const reviewAdminApplication = async ({ id, approved, ...payload }) =>
  (await client.patch(approved ? API.ADMIN_APPLICATION_APPROVE(id) : API.ADMIN_APPLICATION_REJECT(id), payload)).data;
