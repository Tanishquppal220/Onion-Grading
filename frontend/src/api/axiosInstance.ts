import axios from 'axios';
import { notifyRequestFailed, notifyRequestSuccess } from '@/hooks/useBackendStatus';

const api = axios.create({
	baseURL: import.meta.env.VITE_API_URL ?? 'http://localhost:8000',
});

api.interceptors.response.use(
	(response) => {
		notifyRequestSuccess();
		return response;
	},
	(error) => {
		notifyRequestFailed(error);
		return Promise.reject(error);
	}
);

export default api;