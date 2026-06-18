import client from "./client";
import { API } from "../constants/api-endpoints";

export const getMenu = async (outletId) => (await client.get(API.MENU(outletId))).data;
export const getAllMenu = async (outletId) => (await client.get(API.MENU_ALL(outletId))).data;
export const addItem = async (payload) => (await client.post(API.MENU_ADD, payload)).data;
export const updateItem = async ({ id, ...payload }) => (await client.patch(API.MENU_ITEM(id), payload)).data;
export const deleteItem = async (id) => (await client.delete(API.MENU_ITEM(id))).data;
export const setItemAvailability = async ({ id, available }) =>
  (await client.patch(API.MENU_AVAILABILITY(id), { available })).data;
