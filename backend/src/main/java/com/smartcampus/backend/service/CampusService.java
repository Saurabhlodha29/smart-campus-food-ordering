package com.smartcampus.backend.service;

import com.smartcampus.backend.domain.Campus;
import com.smartcampus.backend.repository.CampusRepository;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class CampusService {

    private final CampusRepository campusRepository;

    public CampusService(CampusRepository campusRepository) {
        this.campusRepository = campusRepository;
    }

    public Campus createCampus(Campus campus) {
        return campusRepository.save(campus);
    }

    public List<Campus> getAllCampuses() {
        return campusRepository.findAll();
    }
}