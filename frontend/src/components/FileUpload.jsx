import { useState } from 'react';

function FileUpload({ onUpload, loading }) {
  const [selectedFile, setSelectedFile] = useState(null);

  const handleFileChange = (e) => {
    setSelectedFile(e.target.files[0]);
  };

  const handleSubmit = () => {
    if (!selectedFile) return;
    onUpload(selectedFile);
  };

  return (
    <div className="bg-white rounded-xl shadow-sm p-6 mb-6 flex justify-center items-center">
      <div className="flex items-center gap-4">
        
        <input
          type="file"
          accept=".pdf"
          onChange={handleFileChange}
          className="border-2 border-dashed border-blue-400 rounded-lg p-3 text-sm text-gray-600 cursor-pointer"
        />

        <button
          onClick={handleSubmit}
          disabled={loading || !selectedFile}
          className={`px-6 py-3 rounded-lg text-white font-semibold text-sm transition-all ${
            loading || !selectedFile
              ? 'bg-gray-400 cursor-not-allowed'
              : 'bg-blue-700 hover:bg-blue-800 cursor-pointer'
          }`}
        >
          {loading ? '⌛ Analyzing...' : 'Analyze Report'}
        </button>

      </div>
    </div>
  );
}

export default FileUpload;