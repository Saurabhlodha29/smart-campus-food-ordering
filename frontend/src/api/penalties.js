import client from "./client";
import { API } from "../constants/api-endpoints";

export const myPenalty = async () => (await client.get(API.PENALTY)).data;
export const getPenalty = async (userId) => (await client.get(API.PENALTY_STATUS(userId))).data;
export const waivePenalty = async (userId) => (await client.post(API.PENALTY_WAIVE(userId))).data;
