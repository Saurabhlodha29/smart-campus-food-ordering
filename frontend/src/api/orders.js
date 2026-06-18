import client from "./client";
import { API } from "../constants/api-endpoints";

export const placeOrder = async (payload) => (await client.post(API.ORDERS, payload)).data;
export const myOrders = async (studentId) => (await client.get(API.STUDENT_ORDERS(studentId))).data;
export const managerOrders = async (outletId) => (await client.get(API.OUTLET_ORDERS(outletId))).data;
export const updateStatus = async ({ id, status }) => (await client.patch(API.ORDER_STATUS(id), { status })).data;
export const confirmPickup = async ({ id, otp }) => (await client.post(API.ORDER_PICKUP(id), { otp })).data;
