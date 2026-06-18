import client from "./client";
import { API } from "../constants/api-endpoints";

export const login = async (payload) => (await client.post(API.LOGIN, payload)).data;
export const register = async (payload) => (await client.post(API.REGISTER, payload)).data;
export const verifyEmail = async (payload) => (await client.post(API.VERIFY_EMAIL, payload)).data;
export const resendOtp = async (email) => (await client.post(API.RESEND_OTP, { email })).data;
