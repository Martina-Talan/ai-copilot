import { ChatService } from './chat.service';
import axios from 'axios';
import { Repository } from 'typeorm';
import { Chat } from './entity/chat-entity';

jest.mock('axios');
const mockedAxios = axios as jest.Mocked<typeof axios>;

const mockChatRepo = {
  save: jest.fn(),
  find: jest.fn(),
} as unknown as Repository<Chat>;

describe('ChatService', () => {
  let service: ChatService;

  beforeEach(() => {
    service = new ChatService(mockChatRepo);

    jest.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('should call the AI microservice and return the answer', async () => {
    const mockResponse = {
      answer: {
        kontextAntwort: '1. AI is ...\n2. Extra: ...',
      },
      sources: [{ documentId: 1, filename: 'demo.txt' }],
    };

    mockedAxios.post.mockResolvedValue({ data: mockResponse });

    const result = await service.askQuestion(1, 'What is AI?');

    expect(mockChatRepo.save).toHaveBeenCalledWith({
      documentId: 1,
      role: 'user',
      content: 'What is AI?',
    });

    expect(mockedAxios.post).toHaveBeenCalledWith(
      'http://ai-langchain-service:3001/ask-question',
      { documentId: 1, question: 'What is AI?' },
    );

    expect(mockChatRepo.save).toHaveBeenCalledWith({
      documentId: 1,
      role: 'assistant',
      content: '1. AI is ...\n2. Extra: ...',
    });

    expect(result).toEqual(mockResponse);
  });

  it('should throw an error if the AI service fails', async () => {
    mockedAxios.post.mockRejectedValue(new Error('Service down'));

    await expect(service.askQuestion(1, 'What is AI?')).rejects.toThrow(
      'AI-Service currently not available',
    );

    expect(mockChatRepo.save).toHaveBeenCalledWith({
      documentId: 1,
      role: 'user',
      content: 'What is AI?',
    });
  });

  it('should return chat history ordered by createdAt', async () => {
    const mockHistory = [
      { id: 1, documentId: 1, role: 'user', content: 'Hi' },
      { id: 2, documentId: 1, role: 'assistant', content: 'Hello!' },
    ];
    mockChatRepo.find = jest.fn().mockResolvedValue(mockHistory);

    const result = await service.getChatHistory(1);
    expect(mockChatRepo.find).toHaveBeenCalledWith({
      where: { documentId: 1 },
      order: { createdAt: 'ASC' },
    });
    expect(result).toEqual(mockHistory);
  });
});
