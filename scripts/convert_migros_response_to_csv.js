const fs = require("fs");

const [inputPath, outputPath, category, sourceUrl] = process.argv.slice(2);

if (!inputPath || !outputPath || !category || !sourceUrl) {
  console.error("Usage: node scripts/convert_migros_response_to_csv.js input.json output.csv category sourceUrl");
  process.exit(1);
}

const payload = JSON.parse(fs.readFileSync(inputPath, "utf8"));
const items = payload?.data?.searchInfo?.storeProductInfos || [];

function pickImage(item) {
  return item?.images?.[0]?.urls?.PRODUCT_LIST || item?.images?.[0]?.urls?.PRODUCT_DETAIL || "";
}

function pickPrice(item) {
  return Number(((item?.shownPrice ?? item?.regularPrice ?? 0) / 100).toFixed(2));
}

function csvEscape(value) {
  return `"${String(value ?? "").replace(/"/g, '""')}"`;
}

const rows = [["name", "price", "isStock", "image_url", "category", "source_url"].join(",")];
for (const item of items) {
  rows.push(
    [
      item.name,
      pickPrice(item),
      String(item.status === "IN_SALE"),
      pickImage(item),
      category,
      sourceUrl,
    ]
      .map(csvEscape)
      .join(",")
  );
}

fs.writeFileSync(outputPath, rows.join("\n"), "utf8");
console.log(`written ${items.length}`);
