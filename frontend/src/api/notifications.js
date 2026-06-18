import client from "./client";
import { API } from "../constants/api-endpoints";

export const getNotifs = async () => (await client.get(API.NOTIFICATIONS)).data;
export const markRead = async (id) => (await client.patch(API.NOTIFICATION_READ(id))).data;
export const markAllRead = async () => (await client.patch(API.NOTIFICATIONS_READ_ALL)).data;
