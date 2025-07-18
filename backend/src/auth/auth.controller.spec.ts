import { Test, TestingModule } from '@nestjs/testing';
import { AuthController } from './auth.controller';
import { AuthService } from './auth.service';

describe('AuthController', () => {
  let controller: AuthController;
  let mockAuthService: any;

  beforeEach(async () => {
    mockAuthService = {
      register: jest.fn(),
      login: jest.fn(),
    };

    const module: TestingModule = await Test.createTestingModule({
      controllers: [AuthController],
      providers: [
        {
          provide: AuthService,
          useValue: mockAuthService,
        },
      ],
    }).compile();

    controller = module.get<AuthController>(AuthController);
  });

  it('should call register and return a message', async () => {
    const dto = {
      email: 'user@test.com',
      password: 'testpass',
      username: 'testuser',
    };
    mockAuthService.register.mockResolvedValue({
      message: 'User registered',
      user: { email: dto.email, username: dto.username },
    });

    const result = await controller.register(dto);
    expect(result.user.email).toBe(dto.email);
  });

  it('should call login and return a token', async () => {
    const dto = { email: 'user@test.com', password: 'testpass' };
    mockAuthService.login.mockResolvedValue({ access_token: 'token123' });

    const result = await controller.login(dto);
    expect(result.access_token).toBe('token123');
  });
});
