import { Test, TestingModule } from '@nestjs/testing';
import { ChatController } from './chat.controller';
import { ChatService } from './chat.service';
import { ChatDto } from './dto/chat.dto';
import { ApiResponse } from '../types';

describe('ChatController', () => {
  let controller: ChatController;
  let service: ChatService;

  beforeEach(async () => {
    const module: TestingModule = await Test.createTestingModule({
      controllers: [ChatController],
      providers: [
        {
          provide: ChatService,
          useValue: {
            askQuestion: jest.fn(),
          },
        },
      ],
    }).compile();

    controller = module.get<ChatController>(ChatController);
    service = module.get<ChatService>(ChatService);
  });

  it('should return the AI answer from the service', async () => {
    const inputDto: ChatDto = {
      documentId: 1,
      question: 'What is AI?',
    };

    const mockApiResponse: ApiResponse = {
      answer: '1. AI is ...\n2. Extra info: ...',
      sources: [{ documentId: 1, filename: 'demo.txt' }],
    };

    jest.spyOn(service, 'askQuestion').mockResolvedValue(mockApiResponse);

    const result = await controller.askQuestion(inputDto);

    expect(service.askQuestion).toHaveBeenCalledWith(1, 'What is AI?');
    expect(result).toEqual(mockApiResponse);
  });
});
