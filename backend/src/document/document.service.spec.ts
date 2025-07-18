import { Test, TestingModule } from '@nestjs/testing';
import { DocumentController } from './document.controller';
import { DocumentService } from './document.service';

describe('DocumentController', () => {
  let controller: DocumentController;
  let service: DocumentService;

  const mockDocumentService = {
    saveFileMetadata: jest.fn((filename: string, path: string) =>
      Promise.resolve({
        id: 1,
        filename,
        path,
      }),
    ),
  };
  beforeEach(async () => {
    const module: TestingModule = await Test.createTestingModule({
      controllers: [DocumentController],
      providers: [
        {
          provide: DocumentService,
          useValue: mockDocumentService,
        },
      ],
    }).compile();

    controller = module.get<DocumentController>(DocumentController);
    service = module.get<DocumentService>(DocumentService);
  });

  it('should be defined', () => {
    expect(controller).toBeDefined();
  });

  describe('uploadFile', () => {
    it('should call service.saveFileMetadata with correct parameters', async () => {
      const mockFile = {
        filename: 'test.pdf',
        path: 'uploads/test.pdf',
      } as Express.Multer.File;

      const mockUserId = 1;

      const mockReq = { user: { id: mockUserId } };

      await controller.uploadFiles([mockFile], mockReq);

      expect(service.saveFileMetadata).toHaveBeenCalledWith(
        mockFile.filename,
        mockFile.path,
        mockUserId,
      );
    });
  });
});
