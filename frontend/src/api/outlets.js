import client from "./client";
import { API } from "../constants/api-endpoints";

export const getOutlets = async (campusId) => (await client.get(API.CAMPUS_OUTLETS(campusId))).data;
export const getOutletById = async (id) => (await client.get(API.OUTLET(id))).data;
export const getMyOutlet = async () => (await client.get(API.MY_OUTLET)).data;
export const getCampusOutlets = async (campusId) => (await client.get(API.CAMPUS_OUTLETS_ALL(campusId))).data;
export const toggleOutlet = async (id) => (await client.post(API.OUTLET_TOGGLE(id))).data;
export const launchOutlet = async (id) => (await client.post(API.OUTLET_LAUNCH(id))).data;
