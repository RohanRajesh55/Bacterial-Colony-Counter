/**
 * Export results as CSV or download annotated image
 */

export function exportToCSV(result) {
  const timestamp = new Date().toISOString().split('T')[0];
  const rows = [
    ['Bacterial Colony Counter - Export'],
    [`Date: ${timestamp}`],
    [`Model: ${result.model_used.toUpperCase()}`],
    [''],
    ['Total Colony Count', result.total_count],
    [''],
    ['Class Distribution'],
    ['Class Name', 'Count', 'Avg Confidence']
  ];
  
  result.class_counts.forEach(cls => {
    rows.push([cls.name, cls.count, `${(cls.confidence * 100).toFixed(1)}%`]);
  });
  
  const csvContent = rows.map(row => row.join(',')).join('\n');
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  
  const link = document.createElement('a');
  link.href = url;
  link.download = `colony_analysis_${timestamp}.csv`;
  link.click();
  
  URL.revokeObjectURL(url);
}


export function downloadImage(base64Image, filename = 'annotated_result.png') {
  // Convert base64 to blob
  const byteCharacters = atob(base64Image.split(',')[1] || base64Image);
  const byteNumbers = new Array(byteCharacters.length);
  for (let i = 0; i < byteCharacters.length; i++) {
    byteNumbers[i] = byteCharacters.charCodeAt(i);
  }
  const byteArray = new Uint8Array(byteNumbers);
  const blob = new Blob([byteArray], { type: 'image/png' });
  
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  
  URL.revokeObjectURL(url);
}

export async function downloadPDF(analysisId, labName, researcherName) {
    if (!analysisId) return;
    
    // Construct query parameters
    const params = new URLSearchParams();
    if (labName) params.append('lab_name', labName);
    if (researcherName) params.append('researcher_name', researcherName);
    
    // Use the backend URL
    const API_BASE = import.meta.env.DEV ? "http://localhost:8000/api" : "/api";
    const url = `${API_BASE}/reports/${analysisId}/pdf?${params.toString()}`;
    
    // Trigger download via new window or fetch blob
    // Fetch blob is cleaner for custom filenames but direct link is simpler.
    // Let's use fetch to control the download process better (and Auth if needed later)
    try {
        const response = await fetch(url);
        if (!response.ok) throw new Error("Failed to generate PDF");
        
        const blob = await response.blob();
        const blobUrl = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = blobUrl;
        link.download = `report_${analysisId}_${Date.now()}.pdf`;
        link.click();
        URL.revokeObjectURL(blobUrl);
    } catch (e) {
        console.error("Download failed", e);
        alert("Failed to download PDF report");
    }
}
