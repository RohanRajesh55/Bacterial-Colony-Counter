/**
 * Export results as CSV or download annotated image
 */

/**
 * Escape a field for CSV format
 * - If field contains comma, double-quote, or newline, wrap in double quotes
 * - Escape internal double quotes by doubling them
 */
function escapeCSVField(field) {
  const stringField = String(field);
  if (stringField.includes(',') || stringField.includes('"') || stringField.includes('\n')) {
    return `"${stringField.replace(/"/g, '""')}"`;
  }
  return stringField;
}

export function exportToCSV(result, imageFilename = 'Unknown') {
  const timestamp = new Date().toISOString();
  const rows = [
    ['Bacterial Colony Counter - Export Report'],
    [''],
    ['Field', 'Value'],
    ['Filename', imageFilename],
    ['Colony Count', result.total_count],
    ['Timestamp', timestamp],
    ['Model', result.model_used.toUpperCase()],
  ];

  // Add class distribution if available
  if (result.class_counts && result.class_counts.length > 0) {
    rows.push(['']);
    rows.push(['Class Distribution']);
    rows.push(['Class Name', 'Count', 'Avg Confidence']);
    result.class_counts.forEach(cls => {
      rows.push([cls.name, cls.count, `${(cls.confidence * 100).toFixed(1)}%`]);
    });
  }

  // Apply CSV escaping to all fields and join
  const csvContent = rows.map(row => row.map(escapeCSVField).join(',')).join('\n');
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);

  const link = document.createElement('a');
  link.href = url;
  link.download = `colony_analysis_${timestamp.split('T')[0]}.csv`;
  link.click();

  URL.revokeObjectURL(url);
}

export function downloadImage(base64Image, filename = 'annotated_result.png') {
  // Detect MIME type from data URI prefix
  let mimeType = 'image/png';
  const dataUriMatch = base64Image.match(/^data:([^;]+);base64,/);
  if (dataUriMatch) {
    mimeType = dataUriMatch[1];
  }

  // Convert base64 to blob
  const base64Data = base64Image.split(',')[1] || base64Image;
  const byteCharacters = atob(base64Data);
  const byteNumbers = new Array(byteCharacters.length);
  for (let i = 0; i < byteCharacters.length; i++) {
    byteNumbers[i] = byteCharacters.charCodeAt(i);
  }
  const byteArray = new Uint8Array(byteNumbers);
  const blob = new Blob([byteArray], { type: mimeType });

  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();

  URL.revokeObjectURL(url);
}
