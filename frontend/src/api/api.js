import axios from 'axios';

const BASE_URL = 'http://localhost:5000';

export const uploadReport = async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await axios.post(`${BASE_URL}/doctor`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
    });
    return response.data;
};

export const uploadPatientReport = async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await axios.post(`${BASE_URL}/`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
    });
    return response.data;
};

export const sendChatMessage = async (message, context) => {
    const response = await axios.post(`${BASE_URL}/chatbot`, {
        message,
        context
    });
    return response.data;
};