import { AxiosInstance, AxiosResponse } from 'axios';

import { UploadFile, ContractReview, UploadBatchExpanded } from '../types/contract';

// ------------------------------------------------------------------------


export default class ContractClient {
  private client: AxiosInstance;

  constructor(client: AxiosInstance) {
    this.client = client;
  }

  async upload({
    files,
  }: {
    files: File[];
  }): Promise<AxiosResponse<UploadBatchExpanded>> {
    const payload = new FormData();

    files.forEach((file) => {
      payload.append('files', file);
    });

    return this.client.post('/upload', payload, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  }

  async getAllReviews(
    params: { page?: number; limit?: number }
  ): Promise<AxiosResponse<ContractReview[]>> {
    const query = new URLSearchParams();
    params?.page && query.append('page', params.page.toString());
    params?.limit && query.append('limit', params.limit.toString());

    if (params.page && params.limit) {
      return this.client.get(`/all?${query.toString()}`);
    } else {
      return this.client.get(`/all`);
    }
  }

  async getReview(id: string): Promise<AxiosResponse<ContractReview>> {
    return this.client.get(`/${id}`);
  }

  async getAllUploadedFiles(): Promise<AxiosResponse<UploadFile[]>> {
    return this.client.get('/upload/all');
  }

  async getUpload(id: string): Promise<AxiosResponse<UploadFile>> {
    return this.client.get(`/upload/${id}`);
  }

  async compare(ids: string[]): Promise<AxiosResponse<ContractReview[]>> {
    return this.client.post('/compare', { ids });
  }

}
