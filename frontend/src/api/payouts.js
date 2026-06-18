import client from "./client";
import { API } from "../constants/api-endpoints";

export const ledger = async (date) =>
  (await client.get(API.LEDGER, { params: date ? { date } : undefined })).data;
export const ledgerSummary = async (date) =>
  (await client.get(API.LEDGER_SUMMARY, { params: date ? { date } : undefined })).data;
export const payouts = async () => (await client.get(API.PAYOUTS)).data;
export const campusPayouts = async () => (await client.get(API.CAMPUS_PAYOUTS)).data;
