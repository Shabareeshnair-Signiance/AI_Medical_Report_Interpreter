function ValidationCard({ validation }) {
  if (!validation) return null;

  return (
    <div className={`bg-white rounded-xl shadow-sm overflow-hidden border border-gray-200 mb-6 ${!validation.is_valid ? 'border-t-4 border-t-red-500' : ''}`}>
      
      {/* Header */}
      <div className="bg-gray-50 px-8 py-5 flex justify-between items-center border-b border-gray-200">
        <h2 className="text-2xl font-bold text-gray-900">Validation Details</h2>
        <div className="flex items-center gap-3 font-bold text-lg">
          {validation.is_valid ? (
            <>
              <span>✅</span>
              <span>Status:</span>
              <span className="bg-green-500 text-white px-4 py-1 rounded-md text-sm uppercase">Valid</span>
            </>
          ) : (
            <>
              <span>🚫</span>
              <span>Status:</span>
              <span className="bg-red-500 text-white px-4 py-1 rounded-md text-sm uppercase">Invalid</span>
            </>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="px-8 py-6">
        
        {/* Report Verification */}
        <div className="mb-5">
          <label className="block font-extrabold text-lg mb-2 text-black">Report Verification</label>
          <p className="text-gray-600 text-base">
            {validation.is_valid ? 'Report format verified successfully' : validation.error_message || 'The uploaded file is not a valid medical report.'}
          </p>
        </div>

        {/* Report Type */}
        <div className="mb-5">
          <label className="block font-extrabold text-lg mb-2 text-black">Report Type</label>
          <span className="bg-blue-600 text-white px-4 py-2 rounded-lg font-semibold text-sm">
            {validation.status === 'DUPLICATE' ? '🔄 Existing (Cached)' : validation.status === 'HISTORY_FOUND' ? '📜 Historical Match' : '🆕 New Record'}
          </span>
        </div>

        {/* Divider */}
        <div className="h-px bg-gray-200 my-6"></div>

        {/* Patient Details */}
        <div>
          <h3 className="text-xl font-bold mb-5">Patient Details</h3>
          <div className="grid grid-cols-3 gap-5">
            <div className="text-lg">
              <span className="font-extrabold text-black mr-2">Name:</span>
              <span className="text-blue-700 font-semibold">{validation.patient_name || 'Unknown'}</span>
            </div>
            <div className="text-lg">
              <span className="font-extrabold text-black mr-2">PID:</span>
              <span className="text-blue-700 font-semibold">{validation.pid || 'N/A'}</span>
            </div>
            <div className="text-lg">
              <span className="font-extrabold text-black mr-2">Date:</span>
              <span className="text-blue-700 font-semibold">{validation.report_date || 'Not Found'}</span>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}

export default ValidationCard;