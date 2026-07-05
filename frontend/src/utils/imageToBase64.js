/**
 * Compresses an image file client-side and returns a base64 data URI.
 * Keeps upload payloads small enough to store directly in the database
 * (no cloud storage / S3 needed at this stage of the project).
 */
export function compressImageToBase64(file, { maxWidth = 1000, quality = 0.75 } = {}) {
  return new Promise((resolve, reject) => {
    if (!file) return reject(new Error("No file provided"));
    if (!file.type.startsWith("image/")) {
      return reject(new Error("Please select an image file (JPG, PNG, or WEBP)"));
    }
    if (file.size > 8 * 1024 * 1024) {
      return reject(new Error("Image is too large. Please choose a file under 8MB."));
    }

    const reader = new FileReader();
    reader.onerror = () => reject(new Error("Could not read the selected file"));
    reader.onload = () => {
      const img = new Image();
      img.onerror = () => reject(new Error("Could not load the selected image"));
      img.onload = () => {
        const scale = Math.min(1, maxWidth / img.width);
        const canvas = document.createElement("canvas");
        canvas.width = Math.round(img.width * scale);
        canvas.height = Math.round(img.height * scale);
        const ctx = canvas.getContext("2d");
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        resolve(canvas.toDataURL("image/jpeg", quality));
      };
      img.src = reader.result;
    };
    reader.readAsDataURL(file);
  });
}
