import {createWorker} from 'tesseract.js';

const escapeRegExp = value => value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

function valueForLabel(lines, labels) {
  const labelPattern = labels.map(escapeRegExp).join('|');
  const pattern = new RegExp(`^\\s*(?:${labelPattern})\\s*(?:number|no\\.?)?\\s*[:#-]?\\s*(.*)$`, 'i');
  for (let i = 0; i < lines.length; i += 1) {
    const match = lines[i].match(pattern);
    if (!match) continue;
    const value = match[1].trim();
    if (value) return value;
    if (lines[i + 1]) return lines[i + 1].trim();
  }
  return '';
}

function cleanValue(value) {
  return value.replace(/[|]+$/g, '').replace(/\s{2,}/g, ' ').trim();
}

export function parseDeedOcr(text) {
  const lines = text.split(/\r?\n/).map(line => line.trim()).filter(Boolean);
  const result = {
    deed_number: cleanValue(valueForLabel(lines, ['deed number', 'deed no', 'deed no.'])),
    registration_year: null,
    seller_name: cleanValue(valueForLabel(lines, ['seller name', 'seller'])),
    buyer_name: cleanValue(valueForLabel(lines, ['buyer name', 'buyer'])),
    mouza: cleanValue(valueForLabel(lines, ['mouza'])),
    jl_number: cleanValue(valueForLabel(lines, ['jl number', 'jl no', 'jl no.'])),
    khatian_number: cleanValue(valueForLabel(lines, ['khatian number', 'khatian no', 'khatian no.'])),
    dag_number: cleanValue(valueForLabel(lines, ['dag / plot number', 'dag number', 'dag no', 'dag', 'plot number'])),
    area_decimal: null,
    deed_type: cleanValue(valueForLabel(lines, ['deed type', 'type'])) || 'Sale',
  };

  const year = valueForLabel(lines, ['registration year', 'year']).match(/\d{4}/);
  if (year) result.registration_year = Number(year[0]);

  const area = valueForLabel(lines, ['land area (decimal)', 'land area', 'area (decimal)', 'area']).match(/\d+(?:\.\d+)?/);
  if (area) result.area_decimal = Number(area[0]);

  if (!result.deed_number) {
    const fallback = text.match(/\b[A-Z]{2,10}[-\s]\d{4}[-\s]\d{3}\b/i);
    if (fallback) result.deed_number = fallback[0].replace(/\s+/g, '-').toUpperCase();
  }
  return result;
}

export async function recognizeDeedImage(file) {
  const worker = await createWorker('eng');
  try {
    const {data} = await worker.recognize(file);
    return {text: data.text || '', confidence: data.confidence ?? null};
  } finally {
    await worker.terminate();
  }
}
