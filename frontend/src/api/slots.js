import client from "./client";
import { API } from "../constants/api-endpoints";

export const getSlots = async (outletId) => (await client.get(API.UPCOMING_SLOTS(outletId))).data;
export const createSlot = async (payload) => (await client.post(API.SLOT_CREATE, payload)).data;
export const updateSlot = async ({ id, maxOrders }) => (await client.patch(API.SLOT_CAPACITY(id), { maxOrders })).data;
export const deleteSlot = async (id) => (await client.delete(API.SLOT(id))).data;
