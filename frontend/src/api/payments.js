import client from "./client";
import { API } from "../constants/api-endpoints";

export const initiatePayment = async (orderId) => (await client.post(API.PAYMENT_INIT(orderId))).data;
export const verifyPayment = async (payload) => (await client.post(API.PAYMENT_VERIFY, payload)).data;
export const initiatePenaltyPayment = async (userId) =>
  (await client.post(API.PENALTY_PAYMENT_INIT(userId))).data;
export const verifyPenaltyPayment = async (payload) =>
  (await client.post(API.PENALTY_PAYMENT_VERIFY, payload)).data;
