import { format, formatDistanceToNow } from "date-fns";

export const formatDate = (value) => value ? format(new Date(value), "dd MMM yyyy, h:mm a") : "—";
export const timeAgo = (value) => value ? formatDistanceToNow(new Date(value), { addSuffix: true }) : "—";
