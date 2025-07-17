import { Test, TestingModule } from '@nestjs/testing';
import { AuthService } from './auth.service';
import { getRepositoryToken } from '@nestjs/typeorm';
import { JwtService } from '@nestjs/jwt';
import { User } from '../user/entity/user.entity';
import * as bcrypt from 'bcrypt';

describe('AuthService', () => {
  let service: AuthService;
  let mockUserRepo: any;
  let jwtService: JwtService;

  beforeEach(async () => {
    mockUserRepo = {
      findOne: jest.fn(),
      create: jest.fn(),
      save: jest.fn(),
    };

    const module: TestingModule = await Test.createTestingModule({
      providers: [
        AuthService,
        JwtService,
        {
          provide: getRepositoryToken(User),
          useValue: mockUserRepo,
        },
      ],
    }).compile();

    service = module.get<AuthService>(AuthService);
    jwtService = module.get<JwtService>(JwtService);
  });

  it('should register a new user', async () => {
    mockUserRepo.findOne.mockResolvedValue(null);
    mockUserRepo.create.mockImplementation((user: Partial<User>) => user);
    mockUserRepo.save.mockImplementation(
      (user: Partial<User>) =>
        ({
          id: 1,
          ...user,
        }) as User,
    );

    const result = await service.register('test@example.com', 'password123');
    expect(result.message).toBe('User successfully registered');
    expect(result.user.email).toBe('test@example.com');
  });

  it('should login and return a JWT', async () => {
    const mockUser = {
      id: 1,
      email: 'test@example.com',
      password: await bcrypt.hash('password123', 10),
    };

    mockUserRepo.findOne.mockResolvedValue(mockUser);
    jest.spyOn(jwtService, 'sign').mockReturnValue('mocked-jwt');

    const result = await service.login('test@example.com', 'password123');
    expect(result.access_token).toBe('mocked-jwt');
  });
});
