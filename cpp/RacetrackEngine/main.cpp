#include <vector>
#include <cmath>
#include <algorithm>

struct CarExportData {
    int x, y;
    int vx, vy;
    int state;
    int color;
};

enum class CarState {
    PLAYING = 0,
    CRASHED = 1,
    FINISHED = 2
};

enum class CarColor {
    RED = 0, WHITE = 1, BLUE = 2, BLACK = 3, CUSTOM = 4
};

struct Vector2D {
    int x, y;
    Vector2D(int _x = 0, int _y = 0) : x(_x), y(_y) {}
    Vector2D add(const Vector2D& v) const { return Vector2D(x + v.x, y + v.y); }
    bool equals(const Vector2D& v) const { return x == v.x && y == v.y; }
};

struct Segment {
    Vector2D start;
    Vector2D end;
};

class Track {
private:
    int width, height;
    std::vector<Segment> walls;

    bool onSegment(Vector2D p, Vector2D a, Vector2D b) const {
        return p.x >= std::min(a.x, b.x) && p.x <= std::max(a.x, b.x) &&
            p.y >= std::min(a.y, b.y) && p.y <= std::max(a.y, b.y);
    }
    int orientation(Vector2D p, Vector2D q, Vector2D r) const {
        int val = (q.y - p.y) * (r.x - q.x) - (q.x - p.x) * (r.y - q.y);
        if (val == 0) return 0;
        return (val > 0) ? 1 : 2;
    }
    bool doIntersect(Vector2D p1, Vector2D q1, Vector2D p2, Vector2D q2) const {
        int o1 = orientation(p1, q1, p2);
        int o2 = orientation(p1, q1, q2);
        int o3 = orientation(p2, q2, p1);
        int o4 = orientation(p2, q2, q1);
        if (o1 != o2 && o3 != o4) return true;
        if (o1 == 0 && onSegment(p2, p1, q1)) return true;
        if (o2 == 0 && onSegment(q2, p1, q1)) return true;
        if (o3 == 0 && onSegment(p1, p2, q2)) return true;
        if (o4 == 0 && onSegment(q1, p2, q2)) return true;
        return false;
    }

public:
    Track(int w, int h) : width(w), height(h) {}
    void addWall(int x1, int y1, int x2, int y2) {
        walls.push_back({ Vector2D(x1, y1), Vector2D(x2, y2) });
    }
    bool isCollision(Vector2D start, Vector2D end) const {
        if (end.x < 0 || end.x >= width || end.y < 0 || end.y >= height) return true;
        for (const auto& w : walls) {
            if (doIntersect(start, end, w.start, w.end)) return true;
        }
        return false;
    }
};

class Car {
private:
    Vector2D position;
    Vector2D velocity;
    CarState state;
    CarColor color;

public:
    Car(int startX, int startY, int colorId) {
        reset(Vector2D(startX, startY));
        color = static_cast<CarColor>(colorId);
    }
    void accelerate(int dx, int dy) {
        if (state != CarState::PLAYING) return;
        velocity.x += dx;
        velocity.y += dy;
    }
    Vector2D predictNextPosition() const { return position.add(velocity); }
    void move() { if (state == CarState::PLAYING) position = position.add(velocity); }
    void crash() { state = CarState::CRASHED; velocity = Vector2D(0, 0); }
    void reset(Vector2D startPos) {
        position = startPos;
        velocity = Vector2D(0, 0);
        state = CarState::PLAYING;
    }
    int getX() const { return position.x; }
    int getY() const { return position.y; }
    int getVX() const { return velocity.x; }
    int getVY() const { return velocity.y; }
    int getState() const { return static_cast<int>(state); }
    int getColor() const { return static_cast<int>(color); }
};

class GameSession {
private:
    std::vector<Car> cars;
    Track currentTrack;

    int findCarAtPosition(Vector2D pos, int ignoreIndex) {
        for (size_t i = 0; i < cars.size(); ++i) {
            if (i == ignoreIndex) continue; 

            if (cars[i].getState() == (int)CarState::CRASHED) continue;

            if (cars[i].getX() == pos.x && cars[i].getY() == pos.y) {
                return (int)i;
            }
        }
        return -1;
    }

public:
    GameSession(int w, int h) : currentTrack(w, h) {}

    void addPlayer(int x, int y, int color) { cars.emplace_back(x, y, color); }
    void addWallToTrack(int x1, int y1, int x2, int y2) { currentTrack.addWall(x1, y1, x2, y2); }

    void resetPlayer(int carIndex, int x, int y) {
        if (carIndex >= 0 && carIndex < cars.size()) cars[carIndex].reset(Vector2D(x, y));
    }
    int getCarCount() const { return (int)cars.size(); }

    CarExportData getPlayerExport(int index) const {
        if (index >= 0 && index < cars.size()) {
            const Car& c = cars[index];
            return { c.getX(), c.getY(), c.getVX(), c.getVY(), c.getState(), c.getColor() };
        }
        return { 0,0,0,0, -1, 0 };
    }

    void processInput(int carIndex, int dx, int dy) {
        if (carIndex < 0 || carIndex >= cars.size()) return;
        Car& car = cars[carIndex];

        car.accelerate(dx, dy);

        Vector2D currentPos(car.getX(), car.getY());
        Vector2D nextPos = car.predictNextPosition();

        bool hitWall = currentTrack.isCollision(currentPos, nextPos);

        int hitCarIndex = findCarAtPosition(nextPos, carIndex);

        if (hitWall) {
            car.crash(); 
        }
        else if (hitCarIndex != -1) {
            car.crash();               
            cars[hitCarIndex].crash();  
        }
        else {
            car.move(); 
        }
    }
};

extern "C" {
    __declspec(dllexport) void* Game_new(int width, int height) { return new GameSession(width, height); }
    __declspec(dllexport) void Game_delete(void* game_ptr) { delete (GameSession*)game_ptr; }
    __declspec(dllexport) void Game_add_car(void* game_ptr, int x, int y, int color) { ((GameSession*)game_ptr)->addPlayer(x, y, color); }
    __declspec(dllexport) void Game_add_wall(void* game_ptr, int x1, int y1, int x2, int y2) { ((GameSession*)game_ptr)->addWallToTrack(x1, y1, x2, y2); }
    __declspec(dllexport) int Game_get_car_count(void* game_ptr) { return ((GameSession*)game_ptr)->getCarCount(); }
    __declspec(dllexport) CarExportData Game_get_car_data(void* game_ptr, int index) { return ((GameSession*)game_ptr)->getPlayerExport(index); }
    __declspec(dllexport) void Game_update_car(void* game_ptr, int index, int ax, int ay) { ((GameSession*)game_ptr)->processInput(index, ax, ay); }
    __declspec(dllexport) void Game_reset_car(void* game_ptr, int index, int x, int y) { ((GameSession*)game_ptr)->resetPlayer(index, x, y); }
}