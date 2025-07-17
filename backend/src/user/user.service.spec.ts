import { Test, TestingModule } from '@nestjs/testing';
import { UserService } from './user.service';
import { getRepositoryToken } from '@nestjs/typeorm';
import { User } from './entity/user.entity';
import { Repository } from 'typeorm';

describe('UserService', () => {
  let service: UserService;
  let mockRepo: Partial<Record<keyof Repository<User>, jest.Mock>>;

  beforeEach(async () => {
    mockRepo = {
      find: jest.fn(),
      findOne: jest.fn(),
      clear: jest.fn(),
    };

    const module: TestingModule = await Test.createTestingModule({
      providers: [
        UserService,
        {
          provide: getRepositoryToken(User),
          useValue: mockRepo,
        },
      ],
    }).compile();

    service = module.get(UserService);
  });

  it('should return all users', async () => {
    const users = [{ id: 1, email: 'a@example.com' }];
    mockRepo.find!.mockResolvedValue(users);

    const result = await service.findAll();
    expect(result).toEqual(users);
  });

  it('should find user by email', async () => {
    const user = { id: 1, email: 'a@example.com' };
    mockRepo.findOne!.mockResolvedValue(user);

    const result = await service.findByEmail('a@example.com');
    expect(result).toEqual(user);
  });

  it('should clear all users', async () => {
    await service.deleteAll();
    expect(mockRepo.clear).toHaveBeenCalled();
  });
});
