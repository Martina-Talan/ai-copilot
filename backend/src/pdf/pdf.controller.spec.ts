import { Test, TestingModule } from '@nestjs/testing';
import { PdfController } from './pdf.controller';
import axios from 'axios';
import { ApiResponse } from '../types';
import { HttpException } from '@nestjs/common';

jest.mock('axios');
const mockedAxios = axios as jest.Mocked<typeof axios>;

describe('PdfController', () => {
  let controller: PdfController;

  beforeEach(async () => {
    const module: TestingModule = await Test.createTestingModule({
      controllers: [PdfController],
    }).compile();

    controller = module.get<PdfController>(PdfController);
  });

  it('should return processed PDF data from the AI service', async () => {
    const mockResponse: ApiResponse = {
      answer: 'Extracted content...',
      sources: [],
    };

    mockedAxios.post.mockResolvedValue({ data: mockResponse });

    const result = await controller.viewPdf({ path: 'documents/example.pdf' });

    expect(mockedAxios.post).toHaveBeenCalledWith(
      'http://ai-langchain-service:3001/process-pdf',
      { path: 'documents/example.pdf' },
    );

    expect(result).toEqual(mockResponse);
  });

  it('should throw an error if "path" is missing', async () => {
    await expect(controller.viewPdf({ path: '' } as any)).rejects.toThrow(
      HttpException,
    );
  });

  it('should throw an HttpException on failure', async () => {
    mockedAxios.post.mockRejectedValue(new Error('Service unavailable'));

    await expect(
      controller.viewPdf({ path: 'broken/file.pdf' }),
    ).rejects.toThrow(HttpException);
  });
});
