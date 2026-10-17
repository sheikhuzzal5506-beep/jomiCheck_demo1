const localHostnames = new Set(['localhost', '127.0.0.1', '0.0.0.0']);

// A dropped-files Netlify site has no Python process. Keep local development on
// the real API, while the public demo remains usable when VITE_API_URL is empty.
export const STATIC_DEMO = !import.meta.env.VITE_API_URL && !localHostnames.has(window.location.hostname);

const records = Array.from({length: 50}, (_, index) => {
  const number = index + 1;
  return {
    id: number,
    deed_number: `DEMO-2024-${String(number).padStart(3, '0')}`,
    registration_date: `2024-${String((index % 12) + 1).padStart(2, '0')}-${String((index % 27) + 1).padStart(2, '0')}`,
    registration_year: 2024,
    seller_name: `Demo Person ${String(index * 2 + 1).padStart(2, '0')}`,
    buyer_name: `Demo Person ${String(index * 2 + 2).padStart(2, '0')}`,
    mouza: `Demo Mouza ${(index % 10) + 1}`,
    jl_number: `JL-${101 + index}`,
    khatian_number: `K-${2001 + index}`,
    dag_number: `D-${301 + index}`,
    area_decimal: Number((2.87 + index * 0.14).toFixed(2)),
    deed_type: index % 4 === 1 ? 'Gift' : index % 4 === 2 ? 'Partition' : index % 4 === 3 ? 'Mortgage' : 'Sale',
    office: 'Demo Land Office',
    status: 'DEMO'
  };
});

const fieldsToCompare = [
  ['deed_number', 'Deed number'],
  ['registration_year', 'Registration year'],
  ['seller_name', 'Seller name'],
  ['buyer_name', 'Buyer name'],
  ['mouza', 'Mouza'],
  ['jl_number', 'JL number'],
  ['khatian_number', 'Khatian number'],
  ['dag_number', 'Dag / plot number'],
  ['area_decimal', 'Land area'],
  ['deed_type', 'Deed type']
];

function readChecks() {
  try {
    return JSON.parse(localStorage.getItem('lg_demo_checks') || '[]');
  } catch {
    return [];
  }
}

function saveCheck(check) {
  const checks = readChecks();
  checks.unshift(check);
  localStorage.setItem('lg_demo_checks', JSON.stringify(checks.slice(0, 100)));
  return check;
}

function comparable(value) {
  if (value === null || value === undefined || value === '') return '';
  return String(value).trim().toLowerCase();
}

async function sha256(file) {
  if (!file || !crypto?.subtle) return 'STATIC-DEMO-HASH';
  const buffer = await file.arrayBuffer();
  const digest = await crypto.subtle.digest('SHA-256', buffer);
  return Array.from(new Uint8Array(digest)).map(byte => byte.toString(16).padStart(2, '0')).join('');
}

async function createVerification(formData) {
  const submitted = JSON.parse(formData.get('fields_json') || '{}');
  const file = formData.get('file');
  const reference = records.find(record => comparable(record.deed_number) === comparable(submitted.deed_number));
  const id = readChecks().length + 1;
  const checks = reference
    ? fieldsToCompare.map(([key, label]) => {
        const matches = comparable(submitted[key]) === comparable(reference[key]);
        return {
          name: key,
          status: matches ? 'MATCH' : 'MISMATCH',
          submitted: submitted[key] ?? '',
          reference: reference[key] ?? '',
          detail: `${label} ${matches ? 'matches' : 'does not match'} the synthetic reference.`
        };
      })
    : [{
        name: 'deed_number',
        status: 'NOT_FOUND',
        submitted: submitted.deed_number || '',
        reference: 'No matching record',
        detail: 'No synthetic reference record was found for this deed number.'
      }];
  const status = !reference ? 'UNVERIFIABLE' : checks.every(check => check.status === 'MATCH') ? 'MATCHED' : 'MISMATCH_FOUND';
  const result = {
    id,
    filename: file?.name || 'demo-document',
    file_sha256: await sha256(file),
    status,
    submitted_fields: submitted,
    checks,
    created_at: new Date().toISOString()
  };
  saveCheck({
    id: result.id,
    filename: result.filename,
    deed_number: submitted.deed_number || '',
    status: result.status,
    created_at: result.created_at,
    result
  });
  return result;
}

function dashboardStats() {
  const checks = readChecks();
  return {
    demo_records: records.length,
    verification_requests: checks.length,
    matched: checks.filter(check => check.status === 'MATCHED').length,
    mismatches: checks.filter(check => check.status === 'MISMATCH_FOUND').length,
    recent: checks.slice(0, 5)
  };
}

function pdfSafe(value) {
  return String(value ?? '')
    .replace(/[^\x20-\x7E]/g, '?')
    .replace(/\\/g, '\\\\')
    .replace(/\(/g, '\\(')
    .replace(/\)/g, '\\)');
}

const REPORT_WIDTH = 595.92;
const REPORT_HEIGHT = 842.88;
const REPORT_LEFT = 51;
const REPORT_RIGHT = REPORT_WIDTH - 51;
const REPORT_CONTENT_WIDTH = REPORT_RIGHT - REPORT_LEFT;

function reportRgb(hex) {
  const value = hex.replace('#', '');
  return [0, 2, 4].map(index => (parseInt(value.slice(index, index + 2), 16) / 255).toFixed(3)).join(' ');
}

function reportColor(hex, stroke = false) {
  return `${reportRgb(hex)} ${stroke ? 'RG' : 'rg'}`;
}

function reportWidth(value, font, size) {
  const factor = font === 'F4' ? 0.6 : font === 'F2' ? 0.55 : 0.52;
  return String(value ?? '').length * size * factor;
}

function reportFit(value, font, size, maxWidth) {
  let text = String(value || '');
  if (reportWidth(text, font, size) <= maxWidth) return text;
  while (text && reportWidth(`${text}...`, font, size) > maxWidth) text = text.slice(0, -1);
  return `${text.trim()}...`;
}

function reportWrap(value, font, size, maxWidth) {
  const words = String(value || '').split(/\s+/).filter(Boolean);
  const lines = [];
  let current = '';
  words.forEach(word => {
    const next = current ? `${current} ${word}` : word;
    if (current && reportWidth(next, font, size) > maxWidth) {
      lines.push(current);
      current = word;
    } else {
      current = next;
    }
  });
  if (current || !lines.length) lines.push(current);
  return lines;
}

function reportText(value, x, baseline, font = 'F1', size = 9.2, color = '#475569', align = 'left') {
  const width = reportWidth(value, font, size);
  const start = align === 'center' ? x - width / 2 : align === 'right' ? x - width : x;
  return `${reportColor(color)}\nBT /${font} ${size} Tf 1 0 0 1 ${start.toFixed(2)} ${baseline.toFixed(2)} Tm (${pdfSafe(value)}) Tj ET`;
}

function reportTopText(value, x, top, font = 'F1', size = 9.2, color = '#475569', align = 'left') {
  return reportText(value, x, REPORT_HEIGHT - top - size, font, size, color, align);
}

function reportRoundRect(x, top, width, height, radius, fill = null, stroke = null, lineWidth = 0.8) {
  const y = REPORT_HEIGHT - top - height;
  const r = Math.min(radius, width / 2, height / 2);
  const k = r * 0.5522848;
  const path = [
    `${(x + r).toFixed(2)} ${y.toFixed(2)} m`,
    `${(x + width - r).toFixed(2)} ${y.toFixed(2)} l`,
    `${(x + width - r + k).toFixed(2)} ${y.toFixed(2)} ${(x + width).toFixed(2)} ${(y + r - k).toFixed(2)} ${(x + width).toFixed(2)} ${(y + r).toFixed(2)} c`,
    `${(x + width).toFixed(2)} ${(y + height - r).toFixed(2)} l`,
    `${(x + width).toFixed(2)} ${(y + height - r + k).toFixed(2)} ${(x + width - r + k).toFixed(2)} ${(y + height).toFixed(2)} ${(x + width - r).toFixed(2)} ${(y + height).toFixed(2)} c`,
    `${(x + r).toFixed(2)} ${(y + height).toFixed(2)} l`,
    `${(x + r - k).toFixed(2)} ${(y + height).toFixed(2)} ${x.toFixed(2)} ${(y + height - r + k).toFixed(2)} ${x.toFixed(2)} ${(y + height - r).toFixed(2)} c`,
    `${x.toFixed(2)} ${(y + r).toFixed(2)} l`,
    `${x.toFixed(2)} ${(y + r - k).toFixed(2)} ${(x + r - k).toFixed(2)} ${y.toFixed(2)} ${(x + r).toFixed(2)} ${y.toFixed(2)} c`,
    'h'
  ];
  const commands = [];
  if (fill) commands.push(reportColor(fill));
  if (stroke) commands.push(reportColor(stroke, true), `${lineWidth} w`);
  commands.push(path.join('\n'));
  commands.push(fill && stroke ? 'B' : fill ? 'f' : 'S');
  return commands.join('\n');
}

function reportLine(x1, y1, x2, y2, color = '#e2e8f0', width = 0.8) {
  return `${reportColor(color, true)}\n${width} w\n${x1} ${y1} m ${x2} ${y2} l S`;
}

function reportPill(value, right, top, minWidth = 0) {
  const text = String(value || 'NOT_CHECKED').toUpperCase();
  const palette = {
    MATCHED: ['#166534', '#dcfce7'], MATCH: ['#166534', '#dcfce7'],
    MISMATCH_FOUND: ['#b91c1c', '#fee2e2'], MISMATCH: ['#b91c1c', '#fee2e2'],
    UNVERIFIABLE: ['#b91c1c', '#fee2e2'], REVIEW_REQUIRED: ['#92400e', '#fef3c7'],
    NOT_FOUND: ['#c2410c', '#ffedd5'], OCR_READ: ['#475569', '#e2e8f0'],
    NOT_CHECKED: ['#64748b', '#f1f5f9'], DEMO_ONLY: ['#0369a1', '#e0f2fe'],
    DEMO_RECORD_FOUND: ['#0369a1', '#e0f2fe'], NO_DEMO_RECORD: ['#c2410c', '#ffedd5']
  };
  const [textColor, fillColor] = palette[text] || ['#475569', '#f1f5f9'];
  const width = Math.max(minWidth, reportWidth(text, 'F2', 7.2) + 18);
  return `${reportRoundRect(right - width, top, width, 16, 8, fillColor)}\n${reportTopText(text, right - width / 2, top + 4, 'F2', 7.2, textColor, 'center')}`;
}

function reportCheckTitle(name, status) {
  const key = String(name || '').trim().toLowerCase();
  if (key.includes('ocr')) return 'OCR Extraction Status';
  if (key.includes('reference record') || (key === 'deed_number' && status === 'NOT_FOUND')) return 'Registry Reference Record';
  if (key.includes('reference source')) return 'Registry Reference Source';
  if (key.includes('mutation')) return 'Mutation Record';
  if (key.includes('field comparison')) return 'Field Comparison';
  return String(name || 'Verification Check').replace(/_/g, ' ').replace(/\b\w/g, character => character.toUpperCase());
}

function reportCheckDetail(check) {
  const status = String(check?.status || '').toUpperCase();
  const name = String(check?.name || '').toLowerCase();
  if (name.includes('ocr')) return 'The uploaded image was read in the browser before matching.';
  if (status === 'NOT_FOUND' || name.includes('reference record') || (name === 'deed_number' && status === 'NOT_FOUND')) {
    return 'No matching deed number exists in the synthetic demo database. This outcome does not mean the physical document is counterfeit or fraudulent.';
  }
  if (check?.detail) return String(check.detail).replace('This does not mean the document is fake.', 'This outcome does not mean the physical document is counterfeit or fraudulent.');
  if (check?.submitted || check?.reference) return `Submitted: ${check.submitted || 'Not provided'} - Reference: ${check.reference || 'Not provided'}`;
  return 'No additional diagnostic detail was provided.';
}

function reportCheckHeight(check) {
  if (String(check?.name || '').toLowerCase().includes('ocr')) return 84;
  const lines = reportWrap(reportCheckDetail(check), 'F1', 9.2, REPORT_CONTENT_WIDTH - 26);
  return Math.max(55, 43 + lines.length * 11);
}

function reportCheckCard(check, top) {
  const height = reportCheckHeight(check);
  const status = String(check?.status || 'NOT_CHECKED').toUpperCase();
  const title = reportCheckTitle(check?.name, status);
  const commands = [reportRoundRect(REPORT_LEFT, top, REPORT_CONTENT_WIDTH, height, 8, '#ffffff', '#e2e8f0')];
  commands.push(reportTopText(title, REPORT_LEFT + 13, top + 14, 'F2', 9.8, '#0f172a'));
  commands.push(reportPill(status, REPORT_RIGHT - 13, top + 7));
  if (String(check?.name || '').toLowerCase().includes('ocr')) {
    commands.push(...reportWrap(reportCheckDetail(check), 'F1', 9.2, REPORT_CONTENT_WIDTH - 26).map((line, index) => reportTopText(line, REPORT_LEFT + 13, top + 28 + index * 11, 'F1', 9.2, '#475569')));
    const rawConfidence = check?.confidence ?? String(check?.detail || '').match(/confidence\s*:?\s*(\d+(?:\.\d+)?)/i)?.[1] ?? '';
    const confidence = rawConfidence === '' ? null : Math.max(0, Math.min(100, Number(rawConfidence)));
    const confidenceText = confidence === null || Number.isNaN(confidence) ? 'Not reported' : `${Math.round(confidence)}%`;
    const confidenceTop = top + 57;
    commands.push(reportTopText('Extraction Confidence:', REPORT_LEFT + 13, confidenceTop, 'F1', 8.5, '#64748b'));
    const labelWidth = reportWidth('Extraction Confidence:', 'F1', 8.5);
    commands.push(reportTopText(confidenceText, REPORT_LEFT + 13 + labelWidth + 4, confidenceTop, 'F2', 8.5, '#334155'));
    const trackX = REPORT_LEFT + 13 + labelWidth + reportWidth(confidenceText, 'F2', 8.5) + 18;
    commands.push(reportRoundRect(trackX, confidenceTop + 3, 42, 5, 2.5, '#e2e8f0'));
    if (confidence !== null && !Number.isNaN(confidence)) {
      commands.push(reportRoundRect(trackX, confidenceTop + 3, 42 * confidence / 100, 5, 2.5, confidence < 70 ? '#f59e0b' : '#16a34a'));
      commands.push(reportTopText(confidence < 70 ? '(Low Confidence)' : '(Good Confidence)', trackX + 50, confidenceTop, 'F3', 8.2, confidence < 70 ? '#c2410c' : '#166534'));
    }
  } else {
    commands.push(...reportWrap(reportCheckDetail(check), 'F1', 9.2, REPORT_CONTENT_WIDTH - 26).map((line, index) => reportTopText(line, REPORT_LEFT + 13, top + 27 + index * 11, 'F1', 9.2, '#475569')));
  }
  return {height, stream: commands.join('\n')};
}

function reportFooter(referenceId, pageNumber, totalPages) {
  return [
    reportLine(REPORT_LEFT, REPORT_HEIGHT - 786, REPORT_RIGHT, REPORT_HEIGHT - 786, '#e2e8f0', 0.7),
    reportText(`JomiCheck BD - Verification Reference #${referenceId}`, REPORT_LEFT, REPORT_HEIGHT - 802, 'F1', 7.8, '#64748b'),
    reportText('SYNTHETIC DEMO REPORT - NOT AN OFFICIAL DOCUMENT', REPORT_WIDTH / 2 + 28, REPORT_HEIGHT - 802, 'F1', 7.8, '#64748b', 'center'),
    reportText(`Page ${pageNumber} of ${totalPages}`, REPORT_RIGHT, REPORT_HEIGHT - 802, 'F1', 7.8, '#64748b', 'right')
  ].join('\n');
}

function reportFirstPage(check, checks) {
  const status = String(check?.status || 'UNVERIFIABLE').replace(/_/g, ' ');
  const filename = reportFit(check?.filename || 'Not provided', 'F2', 10.5, REPORT_CONTENT_WIDTH / 2 - 37);
  const deedNumber = check?.submitted_fields?.deed_number || check?.deed_number || 'Not provided';
  const hash = reportFit(check?.file_sha256 || 'STATIC-DEMO-HASH', 'F4', 8.5, REPORT_CONTENT_WIDTH - 26);
  const commands = [
    reportTopText('JomiCheck BD', REPORT_LEFT, 57, 'F2', 20, '#0f172a'),
    reportTopText('Automated Deed & Record Verification System', REPORT_LEFT, 75, 'F1', 10, '#64748b'),
    reportRoundRect(REPORT_RIGHT - 130, 60, 130, 21, 10, '#334155'),
    reportTopText('SYNTHETIC DEMO REPORT', REPORT_RIGHT - 65, 66, 'F2', 7.4, '#ffffff', 'center'),
    reportLine(REPORT_LEFT, REPORT_HEIGHT - 99, REPORT_RIGHT, REPORT_HEIGHT - 99, '#0f172a', 1.2),
    reportRoundRect(REPORT_LEFT, 111, REPORT_CONTENT_WIDTH, 96, 9, '#ffffff', '#e2e8f0'),
    reportTopText('REPORT ID', REPORT_LEFT + 13, 124, 'F2', 8.1, '#64748b'),
    reportTopText(`# ${check?.id || 1}`, REPORT_LEFT + 13, 143, 'F2', 10.5, '#0f172a'),
    reportTopText('OVERALL STATUS', REPORT_LEFT + REPORT_CONTENT_WIDTH / 2 + 4, 124, 'F2', 8.1, '#64748b'),
    reportPill(status, REPORT_LEFT + REPORT_CONTENT_WIDTH - 17, 151, 92),
    reportTopText('FILENAME', REPORT_LEFT + 13, 166, 'F2', 8.1, '#64748b'),
    reportTopText(filename, REPORT_LEFT + 13, 185, 'F2', 10.5, '#0f172a'),
    reportTopText('DEED NUMBER', REPORT_LEFT + REPORT_CONTENT_WIDTH / 2 + 4, 166, 'F2', 8.1, '#64748b'),
    reportTopText(deedNumber, REPORT_LEFT + REPORT_CONTENT_WIDTH / 2 + 4, 185, deedNumber === 'Not provided' ? 'F3' : 'F2', 10.5, deedNumber === 'Not provided' ? '#64748b' : '#0f172a'),
    reportRoundRect(REPORT_LEFT, 220, REPORT_CONTENT_WIDTH, 43, 8, '#ffffff', '#e2e8f0'),
    reportTopText('DOCUMENT SHA-256 FINGERPRINT', REPORT_LEFT + 13, 232, 'F2', 7.8, '#475569'),
    reportTopText(hash, REPORT_LEFT + 13, 248, 'F4', 8.5, '#0f172a'),
    reportRoundRect(REPORT_LEFT + 1, 272, 10, 10, 2, null, '#94a3b8'),
    `${reportColor('#2563eb', true)}\n1.1 w\n${REPORT_LEFT + 3.5} ${REPORT_HEIGHT - 277} m ${REPORT_LEFT + 5.5} ${REPORT_HEIGHT - 279} l ${REPORT_LEFT + 8.5} ${REPORT_HEIGHT - 274.5} l S`,
    reportTopText('Verification Checks & Diagnostics', REPORT_LEFT + 17, 269, 'F2', 12, '#0f172a')
  ];
  return commands;
}

function createDemoPdf(check) {
  const sortedChecks = [...(check?.checks || [])].sort((a, b) => {
    const rank = item => String(item?.name || '').toLowerCase().includes('ocr') ? 0 : String(item?.name || '').toLowerCase().includes('reference record') || item?.status === 'NOT_FOUND' ? 1 : 2;
    return rank(a) - rank(b);
  });
  const legalText = 'A field match is not proof of legal authenticity or ownership. Always verify through authorized official land registry channels.';
  const legalLines = reportWrap(legalText, 'F2', 8.8, REPORT_CONTENT_WIDTH - 39);
  const legalHeight = Math.max(50, 27 + legalLines.length * 11);
  const groups = [];
  let group = [];
  let cursor = 294;
  sortedChecks.forEach(item => {
    const height = reportCheckHeight(item);
    if (group.length && cursor + height > 724) {
      groups.push(group);
      group = [];
      cursor = 86;
    }
    group.push(item);
    cursor += height + 5;
  });
  groups.push(group);
  let legalPage = groups.length - 1;
  let legalTop = Math.max(457, cursor + 9);
  if (legalTop + legalHeight > 769) {
    groups.push([]);
    legalPage = groups.length - 1;
    legalTop = 58;
  }
  const totalPages = groups.length;
  const streams = groups.map((pageChecks, pageIndex) => {
    const commands = pageIndex === 0
      ? reportFirstPage(check, pageChecks)
      : [reportTopText('Verification Checks & Diagnostics (continued)', REPORT_LEFT, 50, 'F2', 12, '#0f172a')];
    let pageCursor = pageIndex === 0 ? 294 : 86;
    pageChecks.forEach(item => {
      const card = reportCheckCard(item, pageCursor);
      commands.push(card.stream);
      pageCursor += card.height + 5;
    });
    if (pageIndex === legalPage) {
      commands.push(reportRoundRect(REPORT_LEFT, legalTop, REPORT_CONTENT_WIDTH, legalHeight, 7, '#ffffff', '#fecaca'));
      commands.push(reportRoundRect(REPORT_LEFT, legalTop, 4, legalHeight, 2, '#dc2626'));
      legalLines.forEach((line, index) => commands.push(reportTopText(line, REPORT_LEFT + 15, legalTop + 16 + index * 11, 'F2', 8.8, '#991b1b')));
    }
    commands.push(reportFooter(check?.id || 1, pageIndex + 1, totalPages));
    return commands.join('\n');
  });

  // Build the file as bytes and record offsets from those exact bytes. This
  // keeps the xref table correct even when a browser handles the blob using a
  // different string encoding.
  const encoder = new TextEncoder();
  const pageCount = streams.length;
  const pageIds = streams.map((_, index) => 3 + index);
  const fontBase = 3 + pageCount;
  const fonts = {F1: fontBase, F2: fontBase + 1, F3: fontBase + 2, F4: fontBase + 3};
  const contentBase = fontBase + 4;
  const contentIds = streams.map((_, index) => contentBase + index);
  const objects = [
    `<< /Type /Catalog /Pages 2 0 R /PageMode /UseNone >>`,
    `<< /Type /Pages /Kids [${pageIds.map(id => `${id} 0 R`).join(' ')}] /Count ${pageCount} >>`,
    ...streams.map((_, index) => `<< /Type /Page /Parent 2 0 R /MediaBox [0 0 ${REPORT_WIDTH} ${REPORT_HEIGHT}] /Resources << /Font << /F1 ${fonts.F1} 0 R /F2 ${fonts.F2} 0 R /F3 ${fonts.F3} 0 R /F4 ${fonts.F4} 0 R >> >> /Contents ${contentIds[index]} 0 R >>`),
    '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
    '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>',
    '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Oblique >>',
    '<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>',
    ...streams.map(stream => `<< /Length ${encoder.encode(stream).length} >>\nstream\n${stream}\nendstream`)
  ];
  const chunks = [];
  let byteLength = 0;
  const append = text => {
    const bytes = encoder.encode(text);
    chunks.push(bytes);
    byteLength += bytes.length;
  };
  append('%PDF-1.4\n');
  const offsets = [];
  objects.forEach((object, index) => {
    offsets.push(byteLength);
    append(`${index + 1} 0 obj\n${object}\nendobj\n`);
  });
  const xrefOffset = byteLength;
  append(`xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`);
  offsets.forEach(offset => append(`${String(offset).padStart(10, '0')} 00000 n \n`));
  append(`trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xrefOffset}\n%%EOF\n`);
  const pdfBytes = new Uint8Array(byteLength);
  let cursorBytes = 0;
  chunks.forEach(chunk => { pdfBytes.set(chunk, cursorBytes); cursorBytes += chunk.length; });
  return new Blob([pdfBytes], {type: 'application/pdf'});
}

async function staticRequest(config) {
  const method = (config.method || 'get').toLowerCase();
  const path = String(config.url || '').replace(/^https?:\/\/[^/]+/, '').split('?')[0];
  let body = config.data;
  if (typeof body === 'string') {
    try { body = JSON.parse(body); } catch { /* FormData or plain text */ }
  }

  if (method === 'post' && path === '/auth/login') {
    if (body?.username !== 'admin' || body?.password !== 'LandGuard123!') {
      const error = new Error('Invalid demo credentials');
      error.response = {status: 401, data: {detail: 'Use admin / LandGuard123!'}};
      throw error;
    }
    return {access_token: 'static-demo-token', user: {username: 'admin', role: 'System Administrator'}};
  }
  if (method === 'get' && path === '/dashboard/stats') return dashboardStats();
  if (method === 'get' && path === '/records/search') {
    const query = comparable(config.params?.q);
    const items = query
      ? records.filter(record => Object.values(record).some(value => comparable(value).includes(query)))
      : records;
    return {items};
  }
  if (method === 'get' && path === '/verifications') return {items: readChecks()};
  if (method === 'get' && path === '/mutations') {
    return {items: records.slice(0, 12).map(record => ({
      id: record.id,
      deed_number: record.deed_number,
      mutation_ref: `MUT-${record.registration_year}-${String(record.id).padStart(3, '0')}`,
      status: 'DEMO',
      note: 'Synthetic mutation reference for interface testing.'
    }))};
  }
  if (method === 'get' && path === '/audit-logs') {
    return {items: readChecks().map(check => ({
      id: check.id,
      created_at: check.created_at,
      actor: 'admin',
      action: 'verification.created',
      detail: `${check.status} · ${check.filename}`
    }))};
  }
  if (method === 'get' && /^\/verifications\/\d+\/report$/.test(path)) {
    const id = Number(path.split('/')[2]);
    const check = readChecks().find(item => item.id === id);
    return createDemoPdf(check?.result || check || {id, status: 'UNVERIFIABLE'});
  }
  if (method === 'post' && path === '/verifications') return createVerification(body);
  throw new Error(`Static demo route not implemented: ${method.toUpperCase()} ${path}`);
}

export function createDemoAdapter() {
  return async config => ({
    data: await staticRequest(config),
    status: 200,
    statusText: 'OK',
    headers: {},
    config,
    request: null
  });
}
