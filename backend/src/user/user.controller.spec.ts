import { Test, TestingModule } from '@nestjs/testing';
import { UserController } from './user.controller';
import { UserService } from './user.service';

describe('UserController', () => {
  let controller: UserController;
  let mockUserService: Partial<UserService>;

  beforeEach(async () => {
    mockUserService = {
      findAll: jest
        .fn()
        .mockResolvedValue([{ id: 1, email: 'test@example.com' }]),
    };

    const module: TestingModule = await Test.createTestingModule({
      controllers: [UserController],
      providers: [
        {
          provide: UserService,
          useValue: mockUserService,
        },
      ],
    }).compile();

    controller = module.get(UserController);
  });

  it('should return all users', async () => {
    const result = await controller.findAll();
    expect(result).toEqual([{ id: 1, email: 'test@example.com' }]);
  });
});
